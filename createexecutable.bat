REM remove any previous builds
RMDIR /s /q dist
RMDIR /s /q build

REM make sure all necessary python dependencies are installed
pip install -r requirements.txt
pip install pyinstaller

REM creat windows executable as one .exe file
pyinstaller --noconsole --onefile --windowed --add-data "assets;assets" --paths "%CD%" --name MaztekSpiritWarrior main.py