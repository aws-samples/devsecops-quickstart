package runners

import "devsecops-quickstart/opa-scan/pkg/utils"

// Terraform Runner
type Terraform struct {
	RunnerInterface
	language   string
	libraries  []string
	parameters map[string]string
}

// NewTerraform creates a new Terraform runner instance
func NewTerraform(parameters map[string]string) *Terraform {
	t := &Terraform{
		language:  "terraform",
		libraries: []string{"terraform_utils", "utils"},
	}

	t.SetParameters(parameters)

	return t
}

// GetLanguage returns runner language
func (t Terraform) GetLanguage() string {
	return t.language
}

// GetRegoLibraries returns Rego libraries used by the runner
func (t Terraform) GetRegoLibraries() []string {
	return t.libraries
}

// SetParameters sets runner parameters
func (t *Terraform) SetParameters(p map[string]string) (err error) {
	t.parameters = p

	return nil
}

// GenerateInput returns terraform plan file content
func (t Terraform) GenerateInput(inputFiles []utils.InputFile) utils.InputFile {
	for _, v := range inputFiles {
		return v
	}

	return utils.InputFile{}
}
