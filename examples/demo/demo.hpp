#pragma once



class Dummy {
    char* useless;
    int numb;
    Dummy() :numb(0), useless("\0"){}

    public:
    void *not_useful(char *str){useless = str;}
};


















struct LongDiff
{

    long diff;

};
