import struct
import time
from pymodbus.client import ModbusTcpClient


class ModbusData:
    def __init__(self, host, port=502):
        self.client = ModbusTcpClient(host, port=port)
        self.client.unit_id = 1

    def connect(self):
        return self.client.connect()

    def disconnect(self):
        self.client.close()

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def _read_two_registers(self, address):
        """Читает два 16-битных регистра и возвращает 32-битное значение (с swap)"""
        r1 = self.client.read_holding_registers(address)
        r2 = self.client.read_holding_registers(address + 1)
        reg1 = r1.registers[0]
        reg2 = r2.registers[0]
        return (reg2 << 16) | reg1

    def _write_two_registers(self, address, value_32bit):
        """Записывает 32-битное значение в два регистра (с swap)"""
        reg2 = (value_32bit >> 16) & 0xFFFF
        reg1 = value_32bit & 0xFFFF
        self.client.write_registers(address, [reg1, reg2])

    def _read_one_register(self, address):
        """Читает один 16-битный регистр"""
        result = self.client.read_holding_registers(address)
        return result.registers[0]

    def _write_one_register(self, address, value):
        """Записывает одно 16-битное значение"""
        self.client.write_registers(address, [value])

    # ==================== FLOAT ====================

    def write_float(self, address, value):
        packed = struct.pack('>f', value)
        value_32bit = struct.unpack('>I', packed)[0]
        self._write_two_registers(address, value_32bit)

    def read_float(self, address):
        value_32bit = self._read_two_registers(address)
        data = struct.pack('>I', value_32bit)
        return struct.unpack('>f', data)[0]

    # ==================== DOUBLE ====================

    def write_double(self, address, value):
        packed = struct.pack('>d', value)
        value_64bit = struct.unpack('>Q', packed)[0]

        # Разбиваем на 4 регистра с swap
        reg4 = (value_64bit >> 48) & 0xFFFF
        reg3 = (value_64bit >> 32) & 0xFFFF
        reg2 = (value_64bit >> 16) & 0xFFFF
        reg1 = value_64bit & 0xFFFF

        self.client.write_registers(address, [reg1, reg2, reg3, reg4])

    def read_double(self, address):
        # Читаем 4 регистра
        r1 = self.client.read_holding_registers(address)
        r2 = self.client.read_holding_registers(address + 1)
        r3 = self.client.read_holding_registers(address + 2)
        r4 = self.client.read_holding_registers(address + 3)

        reg1 = r1.registers[0]
        reg2 = r2.registers[0]
        reg3 = r3.registers[0]
        reg4 = r4.registers[0]

        value_64bit = (reg4 << 48) | (reg3 << 32) | (reg2 << 16) | reg1
        data = struct.pack('>Q', value_64bit)
        return struct.unpack('>d', data)[0]

    # ==================== ULONG (unsigned long) ====================

    def write_ulong(self, address, value):
        self._write_two_registers(address, value)

    def read_ulong(self, address):
        return self._read_two_registers(address)

    # ==================== INT (signed) ====================

    def write_int(self, address, value):
        if value < 0:
            value = 0x100000000 + value
        self._write_one_register(address, value)

    def read_int(self, address):
        value = self._read_one_register(address)
        if value & 0x80000000:
            value = value - 0x100000000
        return value

    # ==================== STRING ====================

    def write_string(self, address, value, max_length=20):
        registers = []
        bytes_data = value.encode('ascii')
        for i in range(0, len(bytes_data), 2):
            if i + 1 < len(bytes_data):
                reg = (bytes_data[i] << 8) | bytes_data[i + 1]
            else:
                reg = (bytes_data[i] << 8) | 0
            registers.append(reg)

        while len(registers) < max_length:
            registers.append(0)

        self.client.write_registers(address, registers)

    def read_string(self, address, length=20):
        registers = []
        for i in range(length):
            result = self.client.read_holding_registers(address + i)
            reg = result.registers[0]
            if reg == 0:
                break
            registers.append(reg)

        bytes_data = bytes()
        for reg in registers:
            bytes_data += bytes([(reg >> 8) & 0xFF, reg & 0xFF])

        while bytes_data and bytes_data[-1] == 0:
            bytes_data = bytes_data[:-1]

        return bytes_data.decode('ascii', errors='ignore')

    # ==================== BMASK (bit mask) ====================

    def write_bmask(self, address, value):
        self._write_one_register(address, value & 0xFFFF)

    def read_bmask(self, address):
        return self._read_one_register(address)


# ==================== ПРИМЕР ИСПОЛЬЗОВАНИЯ ====================

if __name__ == "__main__":
    mb = ModbusData("192.168.53.164")

    if mb.connect():
        print("Подключено успешно\n")

        # FLOAT
        mb.write_float(11099,   150.15)
        print(f"Float: {mb.read_float(11099)}")

        mb.disconnect()
    else:
        print("Не удалось подключиться")
