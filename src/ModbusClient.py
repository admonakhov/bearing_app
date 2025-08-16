import struct
from pyModbusTCP.client import ModbusClient
from src.utils import read_json
import time

def get_registers(parameter, config):
    return [i for i in range(config[parameter][1], config[parameter][1] + config[parameter][2])]


def div_parameters(data, multiplier):
    for key in data.keys():
        data[key] = float(data[key].replace(',', '.')) /  multiplier[key[0]]
    return data

def mult_data(data, multiplier):
    for key in data.keys():
        data[key] = float(data[key].replace(',', '.')) *  multiplier[key[0]]
    return data


def read_TCP_conf(path):
    config = {}
    with open(path, 'r') as _cfg:
        lines = _cfg.read().split('\n')
    for line in lines:
        name, adr, reg, dtype = line.split(' ')
        config[name] = (dtype, int(adr), int(reg))
    return config


def convert_ieee_754_float(regs):
    """Конвертирует 2 регистра Modbus в float (IEEE 754)"""
    if regs and len(regs) == 2:
        raw = struct.pack("<HH", regs[0], regs[1])
        return struct.unpack("<f", raw)[0]
    return None

def float_to_ieee_754_regs(value):
    """Конвертирует float в 2 регистра Modbus (IEEE 754)"""
    if isinstance(value, str):
        value = float(value.replace(',', '.'))

    raw = struct.pack("<f", value)
    return list(struct.unpack("<HH", raw))


def convert_ieee_754_int(regs):
    """Конвертирует 2 регистра Modbus в int (IEEE 754)"""
    if regs and len(regs) == 2:
        return 65536 * regs[1] + regs[0]
    return None

def int_to_ieee_754_regs(value):
    """Конвертирует int в 2 регистра Modbus (IEEE 754 формат)"""
    value = int(value)
    reg0 = value % 65536
    reg1 = value // 65536
    return [reg0, reg1]

def encode_ieee_754(value, dtype='int'):
    if dtype == 'int':
        return int_to_ieee_754_regs(value)
    elif dtype == 'float':
        return float_to_ieee_754_regs(value)


def decode_ieee_754(regs, dtype='int'):
    if dtype == 'int':
        return convert_ieee_754_int(regs)
    elif dtype == 'float':
        return round(convert_ieee_754_float(regs), 3)
    elif dtype == 'byte':
        return regs

def coils_to_registers(coils, bits_per_register=16):
    """
    Преобразует список булевых значений (coils) в список 16-битных регистров.
    """
    registers = []
    for i in range(0, len(coils), bits_per_register):
        reg_bits = coils[i:i+bits_per_register]
        reg_val = 0
        for bit_index, bit in enumerate(reg_bits):
            if bit:
                reg_val |= 1 << bit_index
        registers.append(reg_val)
    return registers

def ask_plc(client, conf, m):
    output = {}

    all_data = client.read_coils(0, 36*16)
    for var in ['Stat','f', 'T', 'N', 'P', 'L', 'M']:
        dtype, adr, reg = conf[var]

        if dtype == 'byte':
            output[var] = all_data[adr * 16: adr * 16 + 8]
        else:
            value = coils_to_registers(all_data[adr * 16: adr * 16 + 32])
            if value:
                output[var] = decode_ieee_754(value, dtype)
                output[var] *= m[var]

            else:
                output[var] = None

    return output



def write_plc(client, adds, values):
    for i in range(len(adds)):
        client.write_single_register(adds[i], values[i])

class Client:
    def __init__(self, host_ip, cfg_path='modbus_adr.cfg'):
        self.client = ModbusClient(host=host_ip, timeout=1)
        self.config = read_TCP_conf(cfg_path)
        self.multiplier = read_json('multiplier.json')

    def __call__(self):
        return ask_plc(self.client, self.config, self.multiplier)

    def send_params(self, params, offsets=None):
        params = div_parameters(params, self.multiplier)
        for param in ['P_tar', 'f_tar', 'P_rate_tar', 'L_lim', 'T_max', 'N_max_lim', 'M_max']:
            value = params[param]
            if param == 'P_tar':
                value = value + offsets['P']
            elif param == 'M_max':
                value = value + offsets['M']
            elif param == 'L_lim':
                value = value + offsets['L']
            write_plc(self.client, get_registers(param, self.config),
                      encode_ieee_754(value, self.config[param][0]))

    def load(self):
        adr = self.config['Cmd'][1]*16 + 0
        self.client.write_single_coil(adr, True)
        print('Loading')

    def unload(self):
        adr = self.config['Cmd'][1]*16 + 0
        self.client.write_single_coil(adr, False)
        print('Unloading')

    def rotate(self):
        adr = self.config['Cmd'][1]*16 + 1
        self.client.write_single_coil(adr, True)

    def stop_rotate(self):
        adr = self.config['Cmd'][1]*16 + 1
        self.client.write_single_coil(adr, False)
        print('Stop Rotation')

    def stop(self):
        self.stop_rotate()
        self.unload()
        print('Everything stopped!')

    def reset(self):
        adr = self.config['Cmd'][1]*16 + 2
        self.client.write_single_coil(adr, True)

    def cont(self):
        self.load()
        self.rotate()
        print('Continuing of test')