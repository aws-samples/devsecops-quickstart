package utils

// IacDocument contains raw IaC file data and other metadata for a given file
type File struct {
	Type     string
	FilePath string
	Data     string
}

type InputFile struct {
	Type     string
	FilePath string
	Data     map[string]interface{}
}
