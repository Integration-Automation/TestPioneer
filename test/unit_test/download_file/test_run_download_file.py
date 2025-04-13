from test_pioneer import execute_yaml

if __name__ == '__main__':
    execute_yaml("download_file.yml")
else:
    execute_yaml("./test/unit_test/download_file/download_file.yml")