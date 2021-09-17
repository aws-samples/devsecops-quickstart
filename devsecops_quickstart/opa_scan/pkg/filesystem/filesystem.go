package filesystem

import (
	"devsecops-quickstart/opa-scan/pkg/filesystem/adapters"
	"devsecops-quickstart/opa-scan/pkg/utils"
	"net/url"
)

// Filesystem struct
type Filesystem struct {
	driver adapters.AddapterInterface
}

// NewFilesystem creates a new Filesystem instance
func NewFilesystem(driver string) *Filesystem {
	var addapter adapters.AddapterInterface

	if driver == "s3" {
		addapter = adapters.NewS3Addapter()
	} else if driver == "local" {
		addapter = adapters.NewLocalAdapter()
	}

	return &Filesystem{
		driver: addapter,
	}
}

func NewFilesystemByPath(path string) *Filesystem {
	addapter := "local"
	u, err := url.Parse(path)
	if err == nil && u.Scheme == "s3" {
		addapter = "s3"
	}

	return NewFilesystem(addapter)
}

func (f Filesystem) PathExists(path string) (bool, error) {
	return f.driver.PathExists(path)
}

func (f Filesystem) Read(path string, experesion string, walk bool) ([]utils.File, error) {
	return f.driver.Read(path, experesion, walk)
}

func (f Filesystem) Write(location map[string]string, content string) error {
	return f.driver.Write(location, content)
}
