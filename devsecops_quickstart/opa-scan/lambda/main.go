package main

import (
	"context"
	"devsecops-quickstart/opa-scan/pkg/app"
	"devsecops-quickstart/opa-scan/pkg/filesystem"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/codepipeline"
)

type MyEvent struct {
	Input           string          `json:"input"`
	Rules           []string        `json:"rules"`
	Parameters      string          `json:"parameters"`
	CodePipelineJob CodePipelineJob `json:"CodePipeline.job"`
}

type CodePipelineParameters struct {
	Rules      []string `json:"rules"`
	Parameters string   `json:"parameters"`
}

// CodePipelineJob represents a job from an AWS CodePipeline event
type CodePipelineJob struct {
	ID        string           `json:"id"`
	AccountID string           `json:"accountId"`
	Data      CodePipelineData `json:"data"`
}

// CodePipelineData represents a job from an AWS CodePipeline event
type CodePipelineData struct {
	ActionConfiguration CodePipelineActionConfiguration `json:"actionConfiguration"`
	InputArtifacts      []CodePipelineInputArtifact     `json:"inputArtifacts"`
	OutPutArtifacts     []CodePipelineOutputArtifact    `json:"outputArtifacts"`
	ArtifactCredentials CodePipelineArtifactCredentials `json:"artifactCredentials"`
	ContinuationToken   string                          `json:"continuationToken"`
}

// CodePipelineActionConfiguration represents an Action Configuration
type CodePipelineActionConfiguration struct {
	Configuration CodePipelineConfiguration `json:"configuration"`
}

// CodePipelineConfiguration represents a configuration for an Action Configuration
type CodePipelineConfiguration struct {
	FunctionName   string `json:"FunctionName"`
	UserParameters string `json:"UserParameters"`
}

// CodePipelineInputArtifact represents an input artifact
type CodePipelineInputArtifact struct {
	Location CodePipelineInputLocation `json:"location"`
	Revision *string                   `json:"revision"`
	Name     string                    `json:"name"`
}

// CodePipelineInputLocation represents a input location
type CodePipelineInputLocation struct {
	S3Location   CodePipelineS3Location `json:"s3Location"`
	LocationType string                 `json:"type"`
}

// CodePipelineS3Location represents an s3 input location
type CodePipelineS3Location struct {
	BucketName string `json:"bucketName"`
	ObjectKey  string `json:"objectKey"`
}

// CodePipelineOutputArtifact represents an output artifact
type CodePipelineOutputArtifact struct {
	Location CodePipelineInputLocation `json:"location"`
	Revision *string                   `json:"revision"`
	Name     string                    `json:"name"`
}

// CodePipelineOutputLocation represents a output location
type CodePipelineOutputLocation struct {
	S3Location   CodePipelineS3Location `json:"s3Location"`
	LocationType string                 `json:"type"`
}

// CodePipelineArtifactCredentials represents CodePipeline artifact credentials
type CodePipelineArtifactCredentials struct {
	SecretAccessKey string `json:"secretAccessKey"`
	SessionToken    string `json:"sessionToken"`
	AccessKeyID     string `json:"accessKeyId"`
}

func HandleLambdaRequest(ctx context.Context, event MyEvent) (string, error) {
	output := make(map[string]string)
	var err error
	var codePipelineJob CodePipelineJob

	// Read event from CodePipeline
	if event.CodePipelineJob.ID != "" {
		codePipelineJob = event.CodePipelineJob
		event = PrepareCodePipelineRequest(codePipelineJob)
	}

	// Run OpaScan
	output["scan_result"] = run(ctx, event)

	// CodePipeline result
	if codePipelineJob.ID != "" {
		_, err = PutCodePipelineResult(ctx, codePipelineJob, output)
		if err != nil {
			log.Fatal(err)
		}
	}

	return output["scan_result"], err
}

func PrepareCodePipelineRequest(job CodePipelineJob) (request MyEvent) {
	fmt.Println("CodePipeline Job ID: " + job.ID)

	userParameters := job.Data.ActionConfiguration.Configuration.UserParameters
	input := job.Data.InputArtifacts[0].Location.S3Location

	var parameters CodePipelineParameters
	json.Unmarshal([]byte(userParameters), &parameters)

	request = MyEvent{
		Rules: parameters.Rules,
		Input: "s3://" + input.BucketName + "/" + input.ObjectKey,
	}

	return request
}

func PutCodePipelineResult(ctx context.Context, job CodePipelineJob, output map[string]string) (*codepipeline.PutJobSuccessResultOutput, error) {
	cfg, err := config.LoadDefaultConfig(context.TODO())
	if err != nil {
		log.Fatalf("unable to load SDK config, %v", err)
	}
	svc := codepipeline.NewFromConfig(cfg)

	// Upload output to S3
	fs := filesystem.NewFilesystem("s3")
	outputLocaltion := map[string]string{
		"bucket": job.Data.OutPutArtifacts[0].Location.S3Location.BucketName,
		"key":    job.Data.OutPutArtifacts[0].Location.S3Location.ObjectKey,
	}
	fmt.Println("Uploading artifact output to S3....")
	fmt.Println(outputLocaltion)
	fs.Write(outputLocaltion, output["scan_result"])

	result, err := svc.PutJobSuccessResult(context.Background(), &codepipeline.PutJobSuccessResultInput{
		JobId:           aws.String(job.ID),
		OutputVariables: output,
	})

	return result, err
}

func run(ctx context.Context, event MyEvent) string {
	fmt.Println("Event:")
	fmt.Println(event)
	// Crear App instance
	c := app.New(event.Rules, event.Parameters)
	rs, err := c.Eval(ctx, event.Input)
	if err != nil {
		log.Fatal(err)
	}

	data, _ := json.Marshal(rs)

	fmt.Println(string(data))
	return string(data)
}

func main() {
	fmt.Println("Running OpaScan.....")

	if os.Getenv("RUN_ON_LAMBDA") == "True" {
		lambda.Start(HandleLambdaRequest)
	} else {
		ctx := context.Background()
		input := flag.String("input", os.Getenv("INPUT"), "Input File/Folder")
		rules := flag.String("rules", os.Getenv("RULES"), "List of rego rules path")
		parameters := flag.String("parameters", os.Getenv("PARAMETERS"), "CF variables")

		flag.Parse()

		event := MyEvent{
			Input:      *input,
			Rules:      strings.Split(*rules, ","),
			Parameters: *parameters,
		}

		// Run OpaScan
		run(ctx, event)
	}
}
