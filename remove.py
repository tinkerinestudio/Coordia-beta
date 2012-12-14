from os import remove
from shutil import move

remove('hello.csv')
move('hello_fixed.csv', 'hello.csv')
