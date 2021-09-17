package runners

import "devsecops-quickstart/opa-scan/pkg/utils"

// RunnerInterface contract definition
type RunnerInterface interface {
	GetLanguage() string
	SetParameters(map[string]string) error
	GenerateInput(inputFiles []utils.InputFile) utils.InputFile
	GetRegoLibraries() []string
}
