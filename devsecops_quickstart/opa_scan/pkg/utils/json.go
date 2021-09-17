package utils

import (
	"encoding/json"
	"fmt"
	"reflect"
)

const (
	// JSONDoc type for json files
	JSONDoc = "json"
)

// AreEqualJSON validate if two json strings are equal
func AreEqualJSON(s1, s2 string) (bool, error) {
	var o1 interface{}
	var o2 interface{}

	errmsg := "error json unmarshalling string: %s. error: %v"

	var err error
	err = json.Unmarshal([]byte(s1), &o1)
	if err != nil {
		return false, fmt.Errorf(errmsg, s1, err.Error())
	}
	err = json.Unmarshal([]byte(s2), &o2)
	if err != nil {
		return false, fmt.Errorf(errmsg, s2, err.Error())
	}

	return reflect.DeepEqual(o1, o2), nil
}
