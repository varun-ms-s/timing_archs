#!/usr/bin/python3

import numpy as np
import json
import re
from os import path
import argparse


def liberty_float(f):
    """

    >>> liberty_float(1.9208818e-02)
    '0.0192088180'

    >>> liberty_float(1.5)
    '1.5000000000'

    >>> liberty_float(1e20)
    '1.000000e+20'

    >>> liberty_float(1)
    '1.0000000000'

    >>> liberty_float(True)
    Traceback (most recent call last):
        ...
    ValueError: True is not a float

    >>> liberty_float(False)
    Traceback (most recent call last):
        ...
    ValueError: False is not a float

    >>> liberty_float(0)
    '0.0000000000'

    >>> liberty_float(None)
    Traceback (most recent call last):
        ...
    ValueError: None is not a float

    >>> liberty_float('hello')
    Traceback (most recent call last):
        ...
    ValueError: 'hello' is not a float


    """
    try:
        f = float(f)
    except (ValueError, TypeError):
        f = None
        raise ValueError("%r is not a float" % f)

    if isinstance(f, bool):
        f = None

    WIDTH = len(str(0.0083333333))

    s = json.dumps(f)
    if 'e' in s:
        a, b = s.split('e')
        if '.' not in a:
            a += '.'
        while len(a)+len(b)+1 < WIDTH:
            a += '0'
        s = "%se%s" % (a, b)
    elif '.' in s:
        while len(s) < WIDTH:
            s += '0'
    else:
        if len(s) < WIDTH:
            s += '.'
        while len(s) < WIDTH:
            s += '0'
    return s


def read_spicetxt(filepath, in_size=7):
    """ Reads the text file generated by the NGSPICE

    Parameters
    ----------
    filepath: str
        Location to a text file.

    in_size: int
        Size of the input vectors
        Default: 7 (taken as per "del_1_7_7")

    Returns
    -------
    input_delay : list
        Input Delay Vector(index_1)

    output_cap : list
        Output Capacitor Vector(index_2)

    timing_vector_2d : np.array(in_size * in_size)
        Timing Table Values.
    """

    with open(filepath, "r") as file_object:
        # read file content
        data = file_object.read()

    input_delay = []
    output_cap = []
    timing_vector = []
    # TODO: To format the vectors as per unit required in .lib file
    for per_in_data in data.split('\n'):
        agr_data = per_in_data.split(':')

        if len(agr_data) == 2:

            if agr_data[0] == 'input_delay':
                in_delay_val = re.sub('[a-z]+', '', agr_data[1])
                input_delay.append(liberty_float(in_delay_val))

        elif len(agr_data) == 4:

            if agr_data[0] == 'out_cap':
                out_cap_val = re.sub('[a-z]+', '', agr_data[1])
                output_cap.append(liberty_float(out_cap_val))

                timing_vector.append(liberty_float(agr_data[-1]))
    # Size of Cap Vector
    cap_size = len(list(set(output_cap)))
    # Size of Input Delay Vector
    delay_size = len(input_delay)
    # Resizing timing 1-D vector to 2-D
    timing_vector_2d = np.array(timing_vector)
    timing_vector_2d.resize(delay_size, cap_size)

    return input_delay, output_cap[:cap_size], timing_vector_2d


def timing_generator(files_folder, unate, related_pin='A'):
    """Generates the timing block in .lib format  """
    # TODO: Make Global variable
    attributes_names = ['cell_fall', 'cell_rise',
                        'fall_transition', 'rise_transition']
    timing_tables = []
    for attr_name in attributes_names:
        file_name = attr_name + '.txt'
        file_location = path.join(files_folder, file_name)
        in_rises, out_caps, timing_table = read_spicetxt(file_location)
        each_attributes = gen_lib(in_rises, out_caps, timing_table, attr_name)
        timing_tables.append(each_attributes)

    timing_str = f"""timing () {{
        {timing_tables[0]}
        {timing_tables[1]}
        {timing_tables[2]}
        related_pin : "{related_pin.upper()}";
        {timing_tables[3]}
        timing_sense : "{unate}";
        timing_type : "combinational";
        }} """

    return timing_str


def gen_lib(in_rises, out_caps, timing_table, attr_name):
    """Format the each attribute content in .lib format """
    in_size = len(in_rises)
    out_size = len(out_caps)
    in_rises_str = ', '.join(in_rises)
    out_caps_str = ', '.join(out_caps)
    tables_data = ['"{}"'.format(', '.join(timing_table[num]))
                   for num in range(len(timing_table))]
    timing_str = ' \ \n \t\t\t'.join(tables_data)

    timing_cell = f"""{attr_name} ("del_1_{in_size}_{out_size}") {{
                    index_1("{in_rises_str}");
                    index_2("{out_caps_str}"); 
                    values({timing_str});
                }}"""
    return timing_cell


if __name__ == '__main__':
    file_location = '../timing_archs/text_files'
    
    parser = argparse.ArgumentParser(
        description="Generates Timing Block using NGSPICE generated .txt files")
    
    parser.add_argument('-loc', metavar='Location', help='Enter the location of all .txt files', 
                        type=str, required=True, default=file_location)
    
    parser.add_argument('-pin', metavar='Relatable Pin', help='Enter the related pin Name', type=str, 
                        required= False, default='A')

    
    argus = parser.parse_args()
    unate = 'undefined'
    timing_info = timing_generator(argus.loc, unate, related_pin=argus.pin)
    print(timing_info)
