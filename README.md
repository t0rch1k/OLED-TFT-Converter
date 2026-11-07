# OLED & TFT Converter

Универсальный инструмент для подготовки и конвертации видео, GIF-анимаций и статичных изображений в битмап-массивы C/C++ (`PROGMEM`) и бинарные файлы для дисплеев микроконтроллеров Arduino, ESP8266, ESP32, RP2040 и STM32.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![Displays](https://img.shields.io/badge/Displays-OLED%20%7C%20TFT%20%7C%20Round%20Watch-orange.svg)

---

## ✨ Возможности

- **Поддержка медиа**: Видео (MP4, AVI, MOV, MKV, WebM), GIF-анимации, изображения (PNG, JPG, BMP, WEBP).
- **Живой предпросмотр**: Отображение формы дисплея (круглый/прямоугольный) и моментальная реакция на ползунки яркости, контраста, дизеринга и кадрирования.
- **Подгонка кадра**: Масштабирование `Заполнить (Crop)` или `Вписать (Letterbox)`.
- **Глубина цвета**:
  - **1-бит Монохром**: Floyd-Steinberg дизеринг или пороговое отсечение.
  - **16-бит RGB565**: точное квантование с выбором порядка байт (MSB/SPI или LSB).
- **Аудио**: Извлечение звуковой дорожки в 8-битный WAV (8 кГц для зуммеров, 16 кГц для динамиков).
- **Экспорт**:
  - Заголовочный файл C/C++ (`.h`) с массивом `PROGMEM`.
  - Бинарный файл (`.vid` / `.rgb565`) для воспроизведения с SD-карты или SPIFFS/LittleFS.

---

## 📟 Поддерживаемые дисплеи

| Профиль | Разрешение | Форма | Цвет / Глубина |
|---|---|---|---|
| **SSD1306 / SH1106** | 128x64 | Прямоугольный | 1-бит монохром |
| **SSD1306** | 128x32 | Прямоугольный | 1-бит монохром |
| **SSD1309 / SSD1327** | 96x96 | Квадратный | 1-бит монохром |
| **SSD1306** | 64x48 | Прямоугольный | 1-бит монохром |
| **Round OLED** | 128x128 | Круглый | 1-бит монохром |
| **GC9A01 / CST816** | 240x240 | Круглый (Watch) | 16-бит RGB565 |
| **Smartwatch** | 280x280 / 360x360 / 466x466 | Круглый (Watch) | 16-бит RGB565 |
| **ST7789** | 240x240 / 135x240 / 240x280 | Прямоугольный | 16-бит RGB565 |
| **ST7789 / ILI9341** | 240x320 | Прямоугольный | 16-бит RGB565 |
| **ST7735** | 128x160 / 128x128 | Прямоугольный | 16-бит RGB565 |
| **ILI9488** | 320x480 | Прямоугольный | 16-бит RGB565 |
| **Пользовательский** | Любой размер | Прямоуг. / Круглый | 1-бит или RGB565 |

---

## 🚀 Запуск

```bash
pip install -r requirements.txt
python oled_converter_gui.py
```

---

## 💻 Примеры использования скетчей

### 1. Монохромный OLED (Adafruit_SSD1306)
```cpp
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "my_animation.h"

Adafruit_SSD1306 display(128, 64, &Wire, -1);

void setup() {
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
}

void loop() {
  for (int f = 0; f < MY_ANIMATION_FRAMES; f++) {
    display.clearDisplay();
    display.drawBitmap(0, 0, my_animation_data[f], 128, 64, SSD1306_WHITE);
    display.display();
    delay(1000 / 15);
  }
}
```

### 2. Цветной TFT/IPS (TFT_eSPI)
```cpp
#include <TFT_eSPI.h>
#include "my_image.h"

TFT_eSPI tft = TFT_eSPI();

void setup() {
  tft.init();
  tft.setRotation(0);
  tft.fillScreen(TFT_BLACK);
  tft.pushImage(0, 0, MY_IMAGE_WIDTH, MY_IMAGE_HEIGHT, my_image_rgb565);
}

void loop() {}
```

---

## 📄 Лицензия

MIT License
