#include "config.h"

/* Defaults = the original "hardcore" behaviour. Must be non-zero data so it stays in .data. */
volatile OotConfig g_ootcfg = {
    {'O', 'O', 'T', 'M', 'C', 'F', 'G', '1'}, 1, sizeof(OotConfig),
    1, 0,
    1, 1, 1, 1, 1, 1, 0, 1,
    {0},
};
