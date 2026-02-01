# Maztek Spirit Warrior

Play in the browser or download windows binary at https://biotomas.itch.io/maztek-spirit-warrior

Each glowing floor tile must be covered by a crystal, otherwise the devil will escape and destroy the world!
Pickup masks to gain new abilities.

Controls:
- WASD: movement
- space: switch ability
- R: restart level

Credits:
- programming: Tomas Balyo, ChatGPT
- music and sound: Meinrad Weiler
- level design Mihai Herda, Tomas Balyo
- visuals: ChatGPT, Grok

## How to install project for development

In Pycharm click in menu
- file
  - Project from version control
    - in the URL field enter `git@github.com:biotomas/ggj26.git`
    - click **clone**
    - click **create virtual environment using the requirements.txt**
- right click on **main.py** and select **run**

## How to build a distributable version
- for a windows build run `createexecutable.bat` then find the `exe` in the `dist` folder.
- for web build install pygbag (`pip install pygbag`) then  run `pygbag main.py` and find the result in `build/web`

## TODO
- [ ] level generator
- [x] web build
- [X] itch.io page
- [x] build
- [x] screenshots, video, ggj page
- [x] sound effects
- [x] video
- [x] story and tutorial cards
- [X] camera movement
- [x] pause after level win
- [X] implement break and walk through boxes
- [X] pickup and swap masks
- [x] reskin the game to look good (box is crystal)
- [x] animated sliding boxes
- [x] good looking animated character
- [x] music
- [x] levels
