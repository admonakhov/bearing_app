<H3> Bearing Test App ver. 0.1.2: </H3>
    - Добавлено отображение нескольких графиков

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
