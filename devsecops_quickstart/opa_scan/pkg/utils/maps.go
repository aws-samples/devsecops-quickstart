package utils

func GetMapValueByIndex(m map[string]interface{}, i int) interface{} {
	count := 0
	for _, v := range m {
		if count == i {
			return v
		}
		count = count + 1
	}

	return ""
}
