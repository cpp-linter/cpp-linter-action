#pragma once // this is bad practice


class Dummy {
    char* useless;
    int numb;
    Dummy() :numb(0), useless("\0"){}
    public:
    void *not_usefull(char &str){useless = str;}
};
