import sysv_ipc
import struct

class SensorSharedMemory:
    def __init__(self, path="/home", project_id='R'):
        """
        Initializes the shared memory reader using the same ftok parameters as the C code.
        """
        # Generate the IPC key using the equivalent of ftok()
        self.key = sysv_ipc.ftok(path, ord(project_id))
        
        # Define the C-struct byte layout for unpacking
        # I = uint32_t (4 bytes)
        # i = int (4 bytes)
        # Layout: 
        # load_cell_sensor (sample, time_stump) -> I, I
        # hall_effect_sensor (sample, time_stump) -> I, I
        # flags[2] -> i, i
        # turn -> i
        self.struct_format = 'IIIIiii'
        self.struct_size = struct.calcsize(self.struct_format)
        self.shm = None

    def connect(self):
        """
        Connects to the existing shared memory segment.
        """
        try:
            # 0 means connect to existing; do not create (IPC_CREAT is not passed)
            self.shm = sysv_ipc.SharedMemory(self.key, 0, 0)
        except sysv_ipc.ExistentialError:
            raise Exception("Shared memory segment not found. Ensure the C program is running.")

    def read_data(self):
        """
        Reads the shared memory segment and unpacks the C struct into a Python dictionary.
        """
        if not self.shm:
            self.connect()
            
        # Read the exact number of bytes matching our struct size
        raw_data = self.shm.read(self.struct_size)
        
        # Unpack the bytes according to the defined format
        unpacked = struct.unpack(self.struct_format, raw_data)
        
        return {
            "load_cell": {
                "sample": unpacked[0],
                "time_stump": unpacked[1]
            },
            "hall_effect": {
                "sample": unpacked[2],
                "time_stump": unpacked[3]
            },
            "sync": {
                "flags": [unpacked[4], unpacked[5]],
                "turn": unpacked[6]
            }
        }

    def detach(self):
        """
        Detaches from the shared memory segment.
        """
        if self.shm:
            self.shm.detach()
            self.shm = None