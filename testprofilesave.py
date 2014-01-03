import csv
import os
from os import remove
from shutil import move

def makeHello(type, value, path):
    #in_file = r'C:\Users\Just\Desktop\temperature.csv'
    #out_file = r'C:\Users\Just\Desktop\hello_fixed.csv'

    #in_file = r'C:\Users\Just\.skeinforge\profiles\extrusion\0.2res\temperature.csv'
    
    in_file = path
    out_file = r'hello_fixed.csv'
    
    csv.register_dialect('tab', delimiter='\t')
    row_reader = csv.reader(open(in_file, "rb"), 'tab')
    row_writer = csv.writer(open(out_file, "wb"), 'tab')

    first_row = row_reader.next()
    row_writer.writerow(first_row)
    for row in row_reader:
        #row[0] = row[0].replace('O', 'o')
        if type in row[0]:
            row[1] = str(value)
            print type
            #print row[-1]
        #print row
        
        if "Extra Shells on Alternating Solid Layer (layers):" in type:
            if "Extra Shells on Base (layers):" in row[0]:
                row[1] = str(value)
            if "Extra Shells on Sparse Layer (layers):" in row[0]:
                row[1] = str(value)
        
        if "Object First Layer Infill Temperature (Celcius):" in type:
            if "Object First Layer Perimeter Temperature (Celcius):" in row[0]:
                row[1] = str(value)
                
        if "Base Temperature (Celcius):" in type:
            if "Interface Temperature (Celcius):" in row[0]:
                row[1] = str(value)
            if "Object Next Layers Temperature (Celcius):" in row[0]:
                row[1] = str(value)
            if "Support Layers Temperature (Celcius):" in row[0]:
                row[1] = str(value)
            if "Supported Layers Temperature (Celcius):" in row[0]:
                row[1] = str(value)
                
        #if "Feed Rate (mm/s):" in type:
        #    if "Perimeter Feed Rate Multiplier (ratio):" in row[0]:
        #        row[1] = str(value)
                
        row_writer.writerow(row)
        #print row, "->", new_row
        #row_writer.writerow(new_row)
    #raw_input("Press Enter to continue...")
    #if not "blah" in somestring: continue

    
def destroyHello(path):
    #remove(r'C:\Users\Just\Desktop\temperature.csv')
    #move(r'C:\Users\Just\Desktop\hello_fixed.csv', r'C:\Users\Just\Desktop\temperature.csv')
    #remove(r'C:\Users\Just\.skeinforge\profiles\extrusion\0.2res\temperature.csv')
    #move(r'hello_fixed.csv', r'C:\Users\Just\.skeinforge\profiles\extrusion\0.2res\temperature.csv')
    remove(path)
    move(r'hello_fixed.csv', path)
