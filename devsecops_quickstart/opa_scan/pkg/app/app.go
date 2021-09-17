package app

import (
	"context"
	"devsecops-quickstart/opa-scan/pkg/filesystem"
	"devsecops-quickstart/opa-scan/pkg/runners"
	"devsecops-quickstart/opa-scan/pkg/utils"
	"embed"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"reflect"
	"regexp"
	"strconv"
	"strings"
	"sync"

	"github.com/open-policy-agent/opa/ast"
	"github.com/open-policy-agent/opa/rego"
)

// Colombo struct
type Colombo struct {
	inputPath  string
	rulesPath  []string
	libsPath   string
	parameters map[string]string
}

// ColomboResult struc
type ColomboResult struct {
	Rules []RuleResult
}

// RuleResult struct definition
type RuleResult struct {
	ID      string `json:"id"`
	Message string `json:"message"`
	Type    string `json:"type"`
	Valid   string `json:"valid"`
}

var (
	app  *Colombo
	once sync.Once
	//go:embed lib/*.rego
	libs embed.FS
)

func newResult() ColomboResult {
	return ColomboResult{}
}

// New Creates a new Colombo Object
func New(rulesPath []string, parameters string) *Colombo {
	// method to ensure singleton behaviour
	once.Do(func() {
		app = &Colombo{
			libsPath: "./lib",
		}
		err := app.setRulesPath(rulesPath)
		if err != nil {
			log.Fatal(err)
		}
		app.SetParameters(parameters)
	})

	return app
}

// SetParameters set parameters to replace in input file
func (c *Colombo) SetParameters(parameters string) {
	c.parameters = map[string]string{}

	// Split paramters by "," allowing lists Example: foo1=hello,foo2=[sub1,sub2]
	r := regexp.MustCompile(`(?:\[.*?\]|[^,])+`)
	parametersSlice := r.FindAllString(parameters, -1)

	for _, param := range parametersSlice {
		keyValue := strings.Split(param, "=")
		key := keyValue[0]
		value := strings.Replace(keyValue[1], "\"", "", -1)

		if strings.HasPrefix(value, "[") {
			valueTemp := strings.Replace(value, "[", "", -1)
			valueTemp = strings.Replace(valueTemp, "]", "", -1)
			valueSlice := strings.Split(valueTemp, ",")
			for i, v := range valueSlice {
				valueSlice[i] = "\"" + v + "\""
			}
			value = "[" + strings.Join(valueSlice, ",") + "]"
		} else if _, err := strconv.Atoi(value); err != nil {
			value = "\"" + value + "\""
		}

		c.parameters[key] = value
	}
}

func (c *Colombo) setRulesPath(rulesPath []string) error {
	for i := 0; i < len(rulesPath); i++ {
		fs := filesystem.NewFilesystemByPath(rulesPath[i])
		if ok, _ := fs.PathExists(rulesPath[i]); ok == false {
			return errors.New("Rules path (" + rulesPath[i] + ") does not exists")
		}
	}
	c.rulesPath = rulesPath
	return nil
}

func (c Colombo) getRules() (map[string]string, error) {
	rules := map[string]string{}

	for i := 0; i < len(c.rulesPath); i++ {
		fs := filesystem.NewFilesystemByPath(c.rulesPath[i])
		rulesPath, err := fs.Read(c.rulesPath[i], "^.+\\.(rego)$", false)
		if err != nil {
			return rules, err
		}
		for _, v := range rulesPath {
			rules[v.FilePath] = v.Data
		}
	}

	return rules, nil
}

// readInputContent Reads input content and returns a map with the path as key and file content as value.
// Input can be a directory path or a file path.
func (c Colombo) readInputContent(path string) ([]utils.InputFile, error) {
	inputFilesJSON := []utils.InputFile{}

	fs := filesystem.NewFilesystemByPath(path)
	inputFiles, err := fs.Read(path, "^.+\\.(json)$", true)
	if err != nil {
		return inputFilesJSON, err
	}

	for _, v := range inputFiles {
		var data map[string]interface{}
		json.Unmarshal([]byte(v.Data), &data)
		inputFilesJSON = append(inputFilesJSON, utils.InputFile{
			Type:     "JSON",
			FilePath: v.FilePath,
			Data:     data,
		})
	}

	return inputFilesJSON, nil
}

func (c Colombo) makeRunner(inputFiles []utils.InputFile) runners.RunnerInterface {
	var runner runners.RunnerInterface

	if len(inputFiles) == 1 {
		//Check if Terraform
		if _, ok := inputFiles[0].Data["terraform_version"]; ok {
			runner = runners.NewTerraform(c.parameters)
		} else {
			runner = runners.NewCloudFormation(c.parameters)
		}
	} else {
		runner = runners.NewCloudFormation(c.parameters)
	}

	return runner
}

func (c Colombo) prepareModules(runner runners.RunnerInterface) (map[string]string, error) {
	fmt.Println("Reading OpaScan Rules...")
	modules, err := c.getRules()
	if err != nil {
		return modules, err
	}

	fmt.Println("Loading Libraries....")
	for _, v := range runner.GetRegoLibraries() {
		f, err := libs.ReadFile("lib/" + v + ".rego")
		if err != nil {
			log.Fatal(err)
		}
		modules[v] = string(f)
	}

	return modules, nil
}

// Eval run evaluation
func (c *Colombo) Eval(ctx context.Context, input string) (ColomboResult, error) {
	fmt.Println("Starting OpaScan Evaluation...")

	// Reads input content and returns a map with the path as key and file content as value
	fmt.Println("Reading Input: " + input)
	c.inputPath = input
	inputFiles, err := c.readInputContent(c.inputPath)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println("Creating final Input....")
	runner := c.makeRunner(inputFiles)
	finalInput := runner.GenerateInput(inputFiles)

	// load Rego lib and rules
	modules, err := c.prepareModules(runner)
	if err != nil {
		log.Fatal(err)
	}

	// Compile the module. The keys are used as identifiers in error messages.
	compiler, err := ast.CompileModules(modules)

	fmt.Println("Checking Compliance.....")
	rego := rego.New(
		rego.Query("data.rules[_].rule"),
		rego.Compiler(compiler),
		rego.Input(finalInput.Data))

	//Run evaluation.
	rs, err := rego.Eval(ctx)
	fmt.Println("Evaluation Finished.")
	if err != nil {
		return newResult(), err
	}
	fmt.Println(rs)
	res := c.parseScanResult(rs)

	return res, err
}

func (c Colombo) parseScanResult(rs rego.ResultSet) ColomboResult {
	result := newResult()

	if len(rs) == 0 {
		return result
	}

	for _, r := range rs {
		for _, exp := range r.Expressions {
			s := reflect.ValueOf(exp.Value)
			for i := 0; i < s.Len(); i++ {
				ret := s.Index(i).Interface()
				data, _ := json.Marshal(ret)
				rule := &RuleResult{}
				json.Unmarshal(data, rule)
				result.Rules = append(result.Rules, *rule)
			}
		}
	}

	return result
}
