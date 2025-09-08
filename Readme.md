<H3> Bearing Test App ver. 1.2.0: </H3>
    - Улучшена производительность <br>
    - Добавлен алгоритм проверки лицензии <br>
    - Реализовано стабильное отображение графика на протяжении всего испытания <br>
    - Очистка кода <br>

<H3> Bearing Test App ver. 1.1.0a: </H3>
    - Исправлен алгоритм выгрузки данных<br>
    - Исправлен алгоритм фильтрации данных<br>
    - Добавлено отображение количества циклов нагружения после остановки<br>
    - Очистка кода <br>

<H3> Bearing Test App ver. 1.0.2b: </H3>
    - Минорные изменения в интерфейсе<br>

<H3> Bearing Test App ver. 1.0.2a: </H3>
    - Исправлена отработка кнопок обнуления для параметра с min-max<br>

<H3> Bearing Test App ver. 1.0.2: </H3>
    - Исправлено определение частоты<br>
    - ПО останавливается вместе с ПЛК <br>
    - Исправлена логика запуска и остановки испытаний <br>


<H3> Bearing Test App ver. 1.0.1a: </H3>
    - Исправлен алгоритм хранения данных<br>

<H3> Bearing Test App ver. 0.1.3: </H3>
    - Исправлены ошибки, улучшена производительность<br>

<br>

<H3> Bearing Test App ver. 0.1.2: </H3>
    - Добавлено отображение нескольких графиков <br>
    - Существенно ускорен сбор данных с ПЛК
<br>

<H3> Bearing Test App ver. 0.1.1: </H3>
    - Добавлено отображение максимального и минимального значений крутящего момента <br>
    - Добавлена выгрузка файла после каждой остановки и запуска испытаний <br>
    - Добавлено осреднение значений на графике методом скользящего среднего - размер окна осреднения задается переменной graph_filter_frame в app.cgf <br>

<br>
Установка приложения: <br>
pip install -r requirements.txt

Сборка приложения: <br>
pyinstaller --onefile --windowed --icon=src\icon.ico --name=BearingTestApp main.py


python -m nuitka   --standalone --onefile  --output-filename=BearingTestApp.exe --enable-plugin=pyside6   --windows-icon-from-ico=src\icon.ico --windows-console-mode=disable --follow-imports   --include-data-files=axis.json=axis.json   --include-data-files=multiplier.json=multiplier.json   --include-data-files=modbus_adr.cfg=modbus_adr.cfg   --include-data-files=app.cfg=app.cfg   --include-data-files=offsets.param=offsets.param   --include-data-files=test_parameters.param=test_parameters.param   main.py
