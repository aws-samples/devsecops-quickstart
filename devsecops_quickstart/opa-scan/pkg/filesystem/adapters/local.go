package adapters

import (
	"devsecops-quickstart/opa-scan/pkg/utils"
	"errors"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"regexp"
)

type AddapterInterface interface {
	PathExists(path string) (bool, error)
	Read(filePath string, experesion string, walk bool) ([]utils.File, error)
	Write(location map[string]string, content string) error
}

type LocalAddapter struct {
	AddapterInterface
}

func NewLocalAdapter() *LocalAddapter {
	return &LocalAddapter{}
}

func (a LocalAddapter) PathExists(path string) (bool, error) {
	_, err := os.Stat(path)
	return !os.IsNotExist(err), err
}

func (a LocalAddapter) Read(path string, experesion string, walk bool) ([]utils.File, error) {
	inputFiles := []utils.File{}
	info, err := os.Stat(path)
	if os.IsNotExist(err) {
		return inputFiles, errors.New("Input file " + path + " does not exist.")
	}

	// Check if is a directory
	if info.IsDir() {
		// Scan inputPath recursively and read all files
		filesPath, err := a.ScanFolderRecursively(path, experesion)
		if err != nil {
			return inputFiles, err
		}

		for i := 0; i < len(filesPath); i++ {
			file, err := a.getFileContent(filesPath[i])
			if err != nil {
				return inputFiles, err
			}
			inputFiles = append(inputFiles, file)
		}
	} else {
		// If is not a dir is a file
		file, err := a.getFileContent(path)
		if err != nil {
			return inputFiles, errors.New("Input File is not a JSON documment")
		}
		inputFiles = append(inputFiles, file)
	}

	return inputFiles, nil
}

func (a LocalAddapter) getFileContent(filePath string) (utils.File, error) {
	content, err := ioutil.ReadFile(filePath)
	if err != nil {
		return utils.File{}, err
	}

	// Convert []byte to string and print to screen
	text := string(content)

	file := utils.File{
		Type:     "JSON",
		FilePath: filePath,
		Data:     text,
	}

	return file, err
}

func (a LocalAddapter) ScanFolderRecursively(path string, experesion string) ([]string, error) {
	libRegEx, e := regexp.Compile(experesion)
	if e != nil {
		log.Fatal(e)
	}

	files := []string{}

	e = filepath.Walk(path, func(path string, info os.FileInfo, err error) error {
		if err == nil && libRegEx.MatchString(info.Name()) {
			files = append(files, path)
		}
		return nil
	})

	return files, e
}

func (a LocalAddapter) Write(location map[string]string, content string) error {
	var err error
	return err
}
