import csv
import os
from os import remove
from shutil import move

def makeHello(value):
    #in_file = r'C:\Users\Just\Desktop\temperature.csv'
    #out_file = r'C:\Users\Just\Desktop\hello_fixed.csv'

    in_file = r'C:\Users\Just\.skeinforge\profiles\extrusion\0.2res\temperature.csv'
    out_file = r'hello_fixed.csv'
    
    csv.register_dialect('tab', delimiter='\t')
    row_reader = csv.reader(open(in_file, "rb"), 'tab')
    row_writer = csv.writer(open(out_file, "wb"), 'tab')

    first_row = row_reader.next()
    row_writer.writerow(first_row)
    for row in row_reader:
        #row[0] = row[0].replace('O', 'o')
        if "Cooling Rate" in row[0]:
            row[1] = str(value)
            #print row[-1]
        #print row
        row_writer.writerow(row)
        #print row, "->", new_row
        #row_writer.writerow(new_row)
    #raw_input("Press Enter to continue...")
    
def destroyHello():
    #remove(r'C:\Users\Just\Desktop\temperature.csv')
    #move(r'C:\Users\Just\Desktop\hello_fixed.csv', r'C:\Users\Just\Desktop\temperature.csv')
    remove(r'C:\Users\Just\.skeinforge\profiles\extrusion\0.2res\temperature.csv')
    move(r'hello_fixed.csv', r'C:\Users\Just\.skeinforge\profiles\extrusion\0.2res\temperature.csv')

