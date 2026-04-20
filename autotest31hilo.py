import time
import xml.etree.ElementTree as ET
from rabota_S_excel import XlsxTagReader
from zapis_i_vivod import ModbusData

mb = ModbusData("192.168.53.164")

if mb.connect():
    print("Подключено успешно\n")


def _get_decimal_places(value) -> int:
    """Определяет количество знаков после запятой у float"""
    if isinstance(value, float):
        str_value = str(value)
        if '.' in str_value:
            return len(str_value.split('.')[1])
    return 0


def _round_to_decimal(value, decimal_places: int) -> float:
    """Округляет значение до указанного количества знаков"""
    if decimal_places >= 0:
        return round(value, decimal_places)
    return value


def process_address(mb, address: int, var_type: str, value):
    """
    Обрабатывает адрес в зависимости от типа переменной.

    :param mb: объект Modbus клиента
    :param address: адрес (строка)
    :param var_type: тип переменной
    :param value: значение для записи
    """
    var_type = str(var_type).strip().lower()

    if var_type == 'bmask':
        mb.write_register(address, int(value))
        time.sleep(2)
        a = mb.read_holding_registers(address, 1)
        is_success = (int(value) == int(a))
        print(f"  Ожидалось: {value}, Получено: {a}")
        return is_success

    elif var_type == 'int':
        mb.write_register(address, int(value))
        time.sleep(2)
        a = mb.read_holding_registers(address, 1)
        is_success = (int(value) == int(a))
        print(f"  Ожидалось: {value}, Получено: {a}")
        return is_success

    elif var_type == 'float':
        mb.write_float(address, float(value))
        time.sleep(2)
        a = mb.read_float(address)
        decimal_places = _get_decimal_places(float(value))
        expected_value = _round_to_decimal(float(value), decimal_places)
        read_value_rounded = _round_to_decimal(float(a), decimal_places)
        is_success = (expected_value == read_value_rounded)
        print(f"  Ожидалось: {expected_value}, Получено: {read_value_rounded}")
        return is_success

    elif var_type == 'ulong':
        mb.write_long(address, int(value))
        time.sleep(2)
        a = mb.read_long(address)
        is_success = (int(value) == int(a))
        print(f"  Ожидалось: {value}, Получено: {a}")
        return is_success

    elif var_type == 'double':
        mb.write_double(address, float(value))
        time.sleep(2)
        a = mb.read_double(address)
        decimal_places = _get_decimal_places(float(value))
        expected_value = _round_to_decimal(float(value), decimal_places)
        read_value_rounded = _round_to_decimal(float(a), decimal_places)
        is_success = (expected_value == read_value_rounded)
        print(f"  Ожидалось: {expected_value}, Получено: {read_value_rounded}")
        return is_success

    else:
        print(f"  Неизвестный тип: {var_type}")
        a = None

    return a


# ==================== ИСПРАВЛЕНИЕ КОДИРОВКИ ====================
def load_xml_with_encoding(file_path):
    """
    Загружает XML файл с автоматическим определением кодировки
    """
    # Пробуем разные кодировки
    encodings = ['utf-8', 'windows-1251', 'cp1251', 'cp866', 'latin-1']

    for encoding in encodings:
        try:
            tree = ET.parse(file_path, parser=ET.XMLParser(encoding=encoding))
            print(f"XML загружен с кодировкой: {encoding}")
            return tree
        except (UnicodeDecodeError, ET.ParseError) as e:
            print(f"  Кодировка {encoding} не подошла: {e}")
            continue

    # Если ничего не подошло, читаем в бинарном режиме и заменяем проблемные символы
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            # Заменяем проблемные байты (0xC8 - это буква 'И' в Windows-1251)
            content = content.replace(b'\xc8', b'?')
            content = content.replace(b'\xe8', b'?')
            content = content.decode('utf-8', errors='replace')

        from io import StringIO
        tree = ET.parse(StringIO(content))
        print("XML загружен с заменой проблемных символов")
        return tree
    except Exception as e:
        raise Exception(f"Не удалось загрузить XML: {e}")


# Загружаем XML
try:
    xml_path = r'C:\\Users\\Ruslan.Osipov\\AppData\\Local\\Programs\\ABAK FC Configurator\\xparams\\xparams_118.xml'
    tree = load_xml_with_encoding(xml_path)
    root = tree.getroot()
    print("XML успешно загружен и распарсен")

except Exception as e:
    print(f"Произошла ошибка: {e}")
    input("Нажмите Enter для выхода...")
    exit()

filtered_elements = []
reader = XlsxTagReader("Копия ModbusMapReport (1).xlsx")

itog_MASS = {}
# Проходим по всем элементам
for elem in root.iter():
    attrib = elem.attrib
    has_hi = 'hi' in attrib
    has_lo = 'lo' in attrib

    if (has_hi or has_lo) and ((attrib.get('tag', 'N/A')[-2] != "_" and attrib.get('tag', 'N/A')[-3] != "_")  or attrib.get('tag', 'N/A')[-2:] == "_1"):
        filtered_elements.append(elem)
        main_value = attrib.get('tag', 'N/A')

        print(f"\n{'=' * 50}")
        print(f"Tag: {main_value}")

        # Ищем в Excel
        result = reader.find_by_tag(main_value)

        if not result:
            print(f"  ОШИБКА: Tag {main_value} не найден в Excel")
            continue

        if len(result) >= 2:
            address = result[0]
            var_type = result[1]
            print(f"  Адрес: {address}, Тип: {var_type}")
        else:
            print(f"  ОШИБКА: Неверный формат результата: {result}")
            continue

        if has_lo:
            itog_MASS[main_value] = [False, False]
            lo_value = attrib['lo']
            print(f"  lo: {lo_value}")
            try:
                success = process_address(mb, int(address) - 1, var_type, lo_value)
                if success:
                    print(f"  >>> ЗНАЧЕНИЯ СОВПАДАЮТ для lo, ЗАПИСЬ ПРОШЛА УСПЕШНО")
                    lo = True
                else:
                    print(f"  >>> ЗНАЧЕНИЯ НЕ СОВПАДАЮТ для lo, ОШИБКА ЗАПИСИ")
                    lo = False

                time.sleep(2)
                success = process_address(mb, int(address) - 1, var_type, str(float(lo_value) - 1))
                if success:
                    print(f"  >>> ЗНАЧЕНИЕ Записано за границей!!!!!, WRONG")
                    lo_1 = False
                else:
                    print(f"  >>> ЗНАЧЕНИЕ lo-1, ЗАПИСЬ НЕ ПРОШЛА, OK")
                    lo_1 = True
                itog_MASS[main_value][0] = lo
                itog_MASS[main_value][1] = lo_1
            except Exception as e:
                print(f"  Ошибка при записи lo: {e}")

        if has_hi:
            if main_value in itog_MASS:
                itog_MASS[main_value].append(False)
                itog_MASS[main_value].append(False)
            else:
                itog_MASS[main_value] = [None, None, False, False]
            hi_value = attrib['hi']
            print(f"  hi: {hi_value}")
            try:
                success = process_address(mb, int(address) - 1, var_type, hi_value)
                if success:
                    print(f"  >>> ЗНАЧЕНИЯ СОВПАДАЮТ для hi, ЗАПИСЬ ПРОШЛА УСПЕШНО, OK")
                    hi = True
                else:
                    print(f"  >>> ЗНАЧЕНИЯ НЕ СОВПАДАЮТ для hi, ОШИБКА ЗАПИСИ, WRONG")
                    hi = False
                time.sleep(2)
                if var_type == "float" and var_type == 'double':
                    success = process_address(mb, int(address) - 1, var_type, str(float(hi_value) + 1))
                else:
                    success = process_address(mb, int(address) - 1, var_type, str(int(hi_value) + 1))

                if success:
                    print(f"  >>> ЗНАЧЕНИЕ Записано за границей!!!!!, WRONG")
                    hi_1 = False
                else:
                    print(f"  >>> ЗНАЧЕНИЕ hi+1, ЗАПИСЬ НЕ ПРОШЛА, OK")
                    hi_1 = True
                itog_MASS[main_value][-2] = hi
                itog_MASS[main_value][-1] = hi_1

            except Exception as e:
                print(f"  Ошибка при записи hi: {e}")

        if 'access' in attrib:
            print(f"  access: {attrib['access']}")

        print(f"{'=' * 50}")

#        input("\nНажмите Enter для продолжения...")

print(f"\nВсего найдено: {len(filtered_elements)}")
print("-" * 50)

for param_name, values in itog_MASS.items():
    if False not in values:
        print(f"✓ {param_name} - прошел проверку (все {len(values)} значений = True)")
    else:
        false_count = values.count(False)
        print(f"✗ {param_name} - НЕ прошел проверку (найдено {false_count} False)")
