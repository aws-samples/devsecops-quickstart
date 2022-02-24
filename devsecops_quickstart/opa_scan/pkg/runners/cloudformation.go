package runners

import (
	"devsecops-quickstart/opa-scan/pkg/utils"
	"encoding/json"
	"log"
	"strings"
)

// CloudFormation Runner
type CloudFormation struct {
	RunnerInterface
	language   string
	libraries  []string
	parameters map[string]string
}

// NewCloudFormation creates a new CloudFormation runner instance
func NewCloudFormation(parameters map[string]string) *CloudFormation {
	c := &CloudFormation{
		language:  "cloudformation",
		libraries: []string{"cloudformation_utils", "utils"},
	}

	c.SetParameters(parameters)

	return c
}

// GetLanguage returns runner language
func (c CloudFormation) GetLanguage() string {
	return c.language
}

// GetRegoLibraries returns Rego libraries used by the runner
func (c CloudFormation) GetRegoLibraries() []string {
	return c.libraries
}

// SetParameters sets runner parameters
func (c *CloudFormation) SetParameters(p map[string]string) (err error) {
	c.parameters = map[string]string{}

	for k, v := range p {
		k := "{\"Ref\":\"" + strings.TrimSpace(k) + "\"}"
		c.parameters[k] = v
	}

	return nil
}

// GenerateInput returns CF template with parameters replaced.
func (c CloudFormation) GenerateInput(inputFiles []utils.InputFile) utils.InputFile {
	finalInput := make(map[string]interface{})

	// Loop all CF files and replace parameters
	for _, inputFile := range inputFiles {
		inputFile.Data = c.Transform(inputFile.Data)
		inputFile, err := json.Marshal(inputFile.Data)
		if err != nil {
			log.Fatal(err)
		}

		inputFileString := c.ReplaceParameters(string(inputFile))

		parseFile := make(map[string]interface{})
		json.Unmarshal([]byte(inputFileString), &parseFile)

		finalInput = utils.Merge(finalInput, parseFile)
	}

	return utils.InputFile{
		Type: "JSON",
		Data: finalInput,
	}
}

// ReplaceParameters Loop all parameters argument and Replace {"Ref":"parameterName"}
func (c CloudFormation) ReplaceParameters(str string) string {
	// Replace all blanK spaces from the input file
	str = strings.Replace(str, " ", "", -1)

	for key, value := range c.parameters {
		str = strings.Replace(str, key, value, -1)
	}

	return str
}

// Transform provider specific template to opascan native format.
func (c CloudFormation) Transform(template map[string]interface{}) map[string]interface{} {
	resources := template["Resources"]

	myMap := resources.(map[string]interface{})
	for key, resource := range myMap {
		r := resource.(map[string]interface{})

		r["address"] = r["Type"].(string) + "." + key
		r["type"] = r["Type"].(string)
		r["name"] = key

		tags := map[string]string{}
		if _, ok := r["Tags"]; ok == true {
			for _, v := range r["Tags"].([]interface{}) {
				foo := v.(map[string]interface{})
				tags[foo["Key"].(string)] = foo["Value"].(string)
			}
		}
		r["tags"] = tags

		delete(r, "Type")
		delete(r, "Tags")
		myMap[key] = r
	}

	template["Resources"] = myMap

	return template
}
