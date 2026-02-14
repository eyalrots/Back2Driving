# ------------------------------------------------
# Compiler settings
# ------------------------------------------------
CC = gcc

# CFLAGS: Compile-time flags
# -Iinclude : Look for headers in the 'include' folder
# -Wall     : Show warnings
# (Removed -llgpio and -pthread from here)
CFLAGS = -Wall -Wextra -Iinclude -I/usr/include

# LDLIBS: Link-time flags (Libraries)
# These must come AFTER the source files in the gcc command
LDLIBS = -llgpio -pthread

# ------------------------------------------------
# Files and Directories
# ------------------------------------------------
TARGET = backend

SRCS =  src/backend.c \
        src/input.c \
        src/logic.c

# ------------------------------------------------
# Build Rules
# ------------------------------------------------

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) $(SRCS) -o $(TARGET) $(LDLIBS)

clean:
	rm -f $(TARGET)

.PHONY: all clean