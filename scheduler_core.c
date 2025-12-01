#include <stdio.h>
#include <stdbool.h>
#include <string.h>

typedef struct 
{
    int day;
    int start;
    int end;
    int week;
} TimeSlot;

#if defined(_WIN32) || defined(__CYGWIN__)
    #define EXPORT __declspec(dllexport)
#else
    #define EXPORT __attribute__((visibility("default")))
#endif

EXPORT int groups_conflict(
    TimeSlot *g1,
    TimeSlot *g2,
    int g1_len,
    int g2_len,
    char *g1_type,
    char *g2_type
)
{
    bool wyklad = false;
    if(strcmp(g1_type, "WYK") == 0 || strcmp(g2_type, "WYK") == 0)
        wyklad = true;
    for(int i = 0; i < g1_len; i++)
    {
        for(int j = 0; j < g2_len; j++)
        {
            if(g1[i].day == g2[j].day && ((g1[i].week == g2[j].week) || (g1[i].week == 0 || g2[j].week == 0)))
            {
                if(!(g1[i].end <= g2[j].start || g2[j].end <= g1[i].start)) 
                    if(wyklad)
                        return 2;
                    else
                        return 1;
            }
        }
           
    }
    return 0;
}
