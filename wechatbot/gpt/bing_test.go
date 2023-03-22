package gpt

import (
	"fmt"
	"testing"
)

func TestBing(t *testing.T) {
	reply, err := BingSearch("今天北京的天气怎么样", "nickname")
        if err != nil{
          t.Error(err)
        }
        fmt.Printf("%+v\n", reply)

}
