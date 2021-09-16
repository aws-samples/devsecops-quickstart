package app

import (
	"errors"
	"reflect"
	"sort"
	"testing"
)

//Test New app function
func TestNewAppEmptyArgs(t *testing.T) {
	a := New([]string{}, "")

	if reflect.TypeOf(a).String() != "*app.Colombo" {
		t.Error("New() is not returning *Colombo instance")
	}
}

// Test assign parameters tu app
func TestNewAppWithMixedParameters(t *testing.T) {
	parameters := "foo1=abc,foo2=225,foo3=[value1,value2,value3]"
	expectedResult := map[string]string{
		"foo1": "\"abc\"",
		"foo2": "225",
		"foo3": "[\"value1\",\"value2\",\"value3\"]",
	}
	a := New([]string{}, "")

	a.SetParameters(parameters)

	if reflect.DeepEqual(a.parameters, expectedResult) == false {
		t.Error("App SetParameters() with string parameters are not mapped correctly")
	}
}

func TestReadLocalAppInputContentNonExistantFile(t *testing.T) {
	expectedError := errors.New("Input file tfplan.json does not exist.")
	inputPath := "tfplan.json"
	a := New([]string{}, "")

	_, err := a.readInputContent(inputPath)
	if err == nil || reflect.DeepEqual(err.Error(), expectedError.Error()) == false {
		t.Error("App readInputContent() must return an error")
	}
}

//Test New app function
func TestReadLocalTerraformAppInputContent(t *testing.T) {
	inputPath := "../../data/tfplan.json"
	a := New([]string{}, "")

	foo, err := a.readInputContent(inputPath)
	if err != nil {
		t.Error(err)
	}

	if len(foo) == 0 {
		t.Error("App Failed to read input content data")
	}
	value := foo[0]

	if value.Data == nil {
		t.Error("App Failed to read input content data")
	}
}

func TestReadS3AppInputContentNonExistantFile(t *testing.T) {
	inputPath := "s3://opascan-codepipeline-output-bucket/opascan-test-pipelin/tf_plan/7DRj2I"
	expectedError := errors.New("S3 object " + inputPath + " does not exist.")
	a := New([]string{}, "")

	_, err := a.readInputContent(inputPath)
	if err == nil || reflect.DeepEqual(err.Error(), expectedError.Error()) == false {
		t.Error("App readInputContent() must return an error")
	}
}

//Test New app function
func TestReadS3TerraformAppInputContent(t *testing.T) {
	inputPath := "s3://opascan-test/terraform-examples/tfplan.json"
	a := New([]string{}, "")

	foo, err := a.readInputContent(inputPath)
	if err != nil {
		t.Error(err)
	}

	value := foo[0]
	if value.Data == nil {
		t.Error("App Failed to read input content data")
	}
}

func TestReadS3CloudFormationFolderAppInputContent(t *testing.T) {
	inputPath := "s3://opascan-test/ecs-refarch-cloudformation"
	files := []string{
		"s3://opascan-test/ecs-refarch-cloudformation/infrastructure/ecs-cluster.json",
		"s3://opascan-test/ecs-refarch-cloudformation/infrastructure/lifecyclehook.json",
		"s3://opascan-test/ecs-refarch-cloudformation/infrastructure/load-balancers.json",
		"s3://opascan-test/ecs-refarch-cloudformation/infrastructure/security-groups.json",
		"s3://opascan-test/ecs-refarch-cloudformation/infrastructure/vpc.json",
		"s3://opascan-test/ecs-refarch-cloudformation/master.json",
	}

	a := New([]string{}, "")

	foo, err := a.readInputContent(inputPath)
	if err != nil {
		t.Error(err)
	}

	keys := make([]string, 0, len(foo))

	for _, v := range foo {
		keys = append(keys, v.FilePath)
	}

	sort.Strings(keys)
	sort.Strings(files)

	if reflect.DeepEqual(files, keys) == false {
		t.Error("readInputContent it's not reading all files for a CF project.")
	}
}

func TestSetS3AppRegoRules(t *testing.T) {
	a := New([]string{}, "")

	inputPath := []string{"s3://test-new-sec-bucket/rego-rules/terraform"}
	err := a.setRulesPath(inputPath)
	if err != nil {
		t.Error("App set S3 rules error: " + err.Error())
	}

	rules, err := a.getRules()

	files := make([]string, 0, len(rules))

	for k := range rules {
		files = append(files, k)
	}

	expectedFiles := []string{"s3://test-new-sec-bucket/rego-rules/terraform/sg_axa.rego"}
	if reflect.DeepEqual(expectedFiles, files) == false {
		t.Error("setRulesPath is not setting rego files correctly")
	}
}
