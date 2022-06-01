package main

import (
	"context"
	"devsecops-quickstart/opa-scan/pkg/app"
	"encoding/json"
	"fmt"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/codepipeline"
	"github.com/aws/aws-sdk-go-v2/service/codepipeline/types"
)

type MyEvent struct {
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
	fmt.Println("Handler started!")

	// WARNING: Uncomment only for testing/debugging purposes, as the event contains temporary credentials
	// passed from pipeline to lambda
	// eventJson, _ := json.Marshal(event)
	// fmt.Println("Event received: " + string(eventJson))

	codePipelineJob := event.CodePipelineJob

	// WARNING: Uncomment only for testing/debugging purposes, as the event contains temporary credentials
	// passed from pipeline to lambda
	// jobJson, _ := json.Marshal(codePipelineJob)
	// fmt.Println("CodePipeline Job: " + string(jobJson))

	userParameters := codePipelineJob.Data.ActionConfiguration.Configuration.UserParameters
	var parameters CodePipelineParameters
	err := json.Unmarshal([]byte(userParameters), &parameters)

	if err != nil {
		return "", err
	}

	inputArtifact := codePipelineJob.Data.InputArtifacts[0].Location.S3Location

	c := app.New(parameters.Rules, event.Parameters)
	result, err := c.Eval(ctx, "s3://"+inputArtifact.BucketName+"/"+inputArtifact.ObjectKey)
	if err != nil {
		return "", err
	}

	resultJson, err := json.Marshal(result)
	if err != nil {
		return "", err
	}

	fmt.Println("Evaluation result: " + string(resultJson))

	return PutCodePipelineResult(ctx, codePipelineJob, result)
}

func PutCodePipelineResult(ctx context.Context, job CodePipelineJob, result app.ColomboResult) (string, error) {
	cfg, err := config.LoadDefaultConfig(context.TODO())
	if err != nil {
		return "", err
	}

	svc := codepipeline.NewFromConfig(cfg)

	var failedRules []app.RuleResult
	for _, ruleResult := range result.Rules {
		if ruleResult.Valid == "false" {
			failedRules = append(failedRules, ruleResult)
		}
	}

	if len(failedRules) > 0 {
		failedJson, err := json.Marshal(failedRules)
		if err != nil {
			return "", err
		}

		fmt.Println("Marking job as failure due to the non-compliant resources: " + string(failedJson))

		_, err = svc.PutJobFailureResult(context.Background(), &codepipeline.PutJobFailureResultInput{
			JobId: aws.String(job.ID),
			FailureDetails: &types.FailureDetails{
				Message: aws.String(string(failedJson)),
				Type:    types.FailureTypeJobFailed,
			},
		})

		if err != nil {
			return "", err
		}
		return "Marked job" + job.ID + " as failure.", nil
	}

	_, err = svc.PutJobSuccessResult(context.Background(), &codepipeline.PutJobSuccessResultInput{
		JobId: aws.String(job.ID),
	})

	if err != nil {
		return "", err
	}

	fmt.Println("Marking job as success, all resources are compliant.")
	return "Marked job" + job.ID + " as success.", nil
}

func main() {
	fmt.Println("Running OpaScan.....")
	lambda.Start(HandleLambdaRequest)
}
