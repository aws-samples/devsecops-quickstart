package adapters

import (
	"archive/zip"
	"context"
	"devsecops-quickstart/opa-scan/pkg/utils"
	"errors"
	"io/ioutil"
	"log"
	"net/url"
	"regexp"
	"strings"
	"sync"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
)

var (
	s3Svc *S3Addapter
	once  sync.Once
)

type S3Addapter struct {
	AddapterInterface
	s3Client *s3.Client
}

// New Creates a new S3Addapter Object
func NewS3Addapter() *S3Addapter {
	// method to ensure singleton behaviour
	once.Do(func() {
		cfg, err := config.LoadDefaultConfig(context.TODO())
		if err != nil {
			log.Fatalf("unable to load SDK config, %v", err)
		}

		svc := s3.NewFromConfig(cfg)

		s3Svc = &S3Addapter{
			s3Client: svc,
		}
	})

	return s3Svc
}
func (a S3Addapter) validateS3Url(path string) (*url.URL, error) {
	u, err := url.Parse(path)
	if err != nil || u.Scheme != "s3" {
		return u, errors.New("Url " + path + " is not valid S3 url.")
	}

	u.Path = strings.Replace(u.Path, "/", "", 1)

	return u, nil
}

func (a S3Addapter) PathExists(path string) (bool, error) {
	// Validate S3 url
	u, err := a.validateS3Url(path)
	if err != nil {
		return false, err
	}

	resp, err := a.s3Client.ListObjectsV2(context.Background(), &s3.ListObjectsV2Input{
		Bucket: aws.String(u.Host),
		Prefix: aws.String(u.Path),
	})

	return len(resp.Contents) > 0, nil
}

func (a S3Addapter) Read(filePath string, experesion string, walk bool) ([]utils.File, error) {
	inputFiles := []utils.File{}

	// Validate Regular expresion
	libRegEx, err := regexp.Compile(experesion)
	if err != nil {
		return inputFiles, err
	}

	// Validate S3 url
	u, err := a.validateS3Url(filePath)

	resp, err := a.s3Client.ListObjectsV2(context.Background(), &s3.ListObjectsV2Input{
		Bucket: aws.String(u.Host),
		Prefix: aws.String(u.Path),
		//Delimiter: aws.String("/"),
		//StartAfter: aws.String(key),
	})
	if err != nil {
		return inputFiles, err
	}

	for _, item := range resp.Contents {
		if err == nil && libRegEx.MatchString(*item.Key) {
			file, err := a.readContent(u.Host, *item.Key)
			if err != nil {
				return inputFiles, err
			}
			inputFiles = append(inputFiles, file)
		}
	}

	if len(inputFiles) == 0 {
		return inputFiles, errors.New("S3 object " + filePath + " does not exist.")
	}

	return inputFiles, nil
}

func (a S3Addapter) readContent(bucket string, key string) (utils.File, error) {
	ctx := context.Background()
	req, err := a.s3Client.GetObject(ctx, &s3.GetObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		return utils.File{}, err
	}

	s3objectBytes, err := ioutil.ReadAll(req.Body)

	file := utils.File{
		Type:     "S3",
		FilePath: "s3://" + bucket + "/" + key,
		Data:     string(s3objectBytes),
	}

	return file, nil

	/*zipReader, err := zip.NewReader(bytes.NewReader(s3objectBytes), int64(len(s3objectBytes)))
	//If err is not nil, it's because is not a zip file.
	if err != nil {
		return string(s3objectBytes), nil
	}

	// Read all the files from zip archive
	//TODO improve this
	for _, zipFile := range zipReader.File {
		foo, err := readZipFile(zipFile)
		if err != nil {
			return string(s3objectBytes), err
		}
		s3objectBytes = foo
	}

	return string(s3objectBytes), nil*/
}

func readZipFile(zf *zip.File) ([]byte, error) {
	f, err := zf.Open()
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return ioutil.ReadAll(f)
}

func (a S3Addapter) Write(location map[string]string, content string) error {
	ctx := context.Background()

	_, err := a.s3Client.PutObject(ctx, &s3.PutObjectInput{
		Bucket:             aws.String(location["bucket"]),
		Key:                aws.String(location["key"]),
		Body:               strings.NewReader(content), // bytes.NewReader(buffer),
		ContentDisposition: aws.String("attachment"),
		// ContentLength:      aws.Int64(int64(len(buffer))),
		// ContentType:        aws.String(http.DetectContentType(buffer)),
		// ServerSideEncryption: aws.String("AES256"),
	})

	return err
}
