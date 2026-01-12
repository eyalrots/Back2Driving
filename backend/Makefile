# ------------------------------------------------
# Compiler settings
# ------------------------------------------------
CC = gcc

# Flags:
# -Iinclude : Look for headers in the 'include' folder
# -pthread  : Required for threads
# -Wall     : Show warnings
CFLAGS = -Wall -Wextra -Iinclude -pthread

# ------------------------------------------------
# Files and Directories
# ------------------------------------------------
# The final executable name
TARGET = backend

# The source files
SRCS = src/main.c

# ------------------------------------------------
# Build Rules
# ------------------------------------------------

all: $(TARGET)

# Compile everything in one go.
# This creates the 'OS' executable directly without leaving .o files.
$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) $(SRCS) -o $(TARGET)

# Clean only deletes the executable (since no .o files are ever made)
clean:
	rm -f $(TARGET)

.PHONY: all clean