"""Пять страниц обзора продукта из существующих иллюстраций и чисел, без запуска детектора."""
from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
H=Path(__file__).resolve().parent;A=H/'assets';W=960;HEIGHT=675
for name,file in [('RU','DejaVuSans.ttf'),('RUB','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(name,str(H/'fonts'/file)))
pdfmetrics.registerFontFamily('RU',normal='RU',bold='RUB',italic='RU',boldItalic='RUB')
P=H/'Обзор_решения.pdf';c=canvas.Canvas(str(P),pagesize=(W,HEIGHT),pageCompression=1)
c.setTitle('Обнаружение препятствий перед беспилотным поездом');c.setAuthor('');c.setSubject('Итоговое решение: примеры, алгоритм, производительность и ограничения')
INK='#262b3b';PURPLE='#673492';MUTED='#626575';LIGHT='#f4f0f8';LINE='#e2dce8';PINK='#ce2871'
def para(s,x,top,width,size=16,color=INK,bold=False,leading=None):
 st=ParagraphStyle('p',fontName='RUB' if bold else 'RU',fontSize=size,leading=leading or size*1.32,textColor=HexColor(color),spaceAfter=0)
 p=Paragraph(s,st);w,h=p.wrap(width,HEIGHT);assert top+h<HEIGHT-25,(s[:70],top,h);p.drawOn(c,x,HEIGHT-top-h);return top+h

def box(x,top,w,h,fill=LIGHT):
 c.setFillColor(HexColor(fill));c.roundRect(x,HEIGHT-top-h,w,h,10,stroke=0,fill=1)
def line(x1,top,x2):c.setStrokeColor(HexColor(LINE));c.setLineWidth(1);c.line(x1,HEIGHT-top,x2,HEIGHT-top)
def page(n,label):
 c.setFillColor(HexColor(PURPLE));c.rect(0,HEIGHT-9,W,9,stroke=0,fill=1)
 para(label.upper(),46,25,800,10,PURPLE,bold=True)
 c.setFillColor(HexColor(MUTED));c.setFont('RU',9);c.drawString(46,19,'Обнаружение препятствий по данным лидара');c.drawRightString(W-46,19,str(n))
def pic(name,x,top,maxw,maxh):
 image=ImageReader(str(A/(name+'.png')));iw,ih=image.getSize();factor=min(maxw/iw,maxh/ih);w=iw*factor;h=ih*factor;c.drawImage(image,x+(maxw-w)/2,HEIGHT-top-h,w,h,mask='auto');return top+h

def title(text):return para(text,46,49,868,29,PURPLE,bold=True,leading=35)
def table(headers,rows,x,top,width,col_widths,row_h=38):
 c.setFillColor(HexColor(PURPLE));c.roundRect(x,HEIGHT-top-row_h,width,row_h,5,stroke=0,fill=1)
 for i,h in enumerate(headers):para(h,x+sum(col_widths[:i])+12,top+10,col_widths[i]-20,12,'#ffffff',bold=True)
 for j,row in enumerate(rows):
  y=top+row_h*(j+1)
  if j%2==0:box(x,y,width,row_h,'#f6f4f8')
  for i,t in enumerate(row):para(str(t),x+sum(col_widths[:i])+12,y+10,col_widths[i]-20,13)
 return top+row_h*(len(rows)+1)

def comma(x):return f'{x:.1f}'.replace('.',',')
# 1. Задача и продукт.
page(1,'Задача и решение')
para('Обнаружение препятствий<br/>перед беспилотным поездом',46,54,865,34,PURPLE,bold=True,leading=42)
para('Обрабатываем облако точек лидара, определяем препятствие в зоне движения поезда и передаём результат в ROS 2.',46,169,505,20,leading=28)
para('Работа на CPU<br/>Docker для ROS 2 Humble',46,273,505,17,bold=True,leading=26)
box(610,163,304,171)
para('до 99,4 м',632,184,266,40,PURPLE,bold=True)
para('Проверенные примеры<br/>предоставленных<br/>синтетических данных',632,244,265,16,bold=True,leading=22)
pic('product_flow',46,357,868,130)
box(46,507,419,107);box(495,507,419,107)
para('Что получает система',62,521,383,16,PURPLE,bold=True)
para('Облако точек с текущего лидара<br/>или из записи ROS 2 bag.',62,552,383,15)
para('Что передаёт потребителю',511,521,383,16,PURPLE,bold=True)
para('Признак препятствия, расстояние,<br/>состояние решения и диагностику.',511,552,383,15)
c.showPage()
# 2. Три реальных сохранённых примера.
page(2,'Примеры обнаружения');title('Что обнаруживает система')
para('Три сценария из предоставленных синтетических данных',46,99,868,16)
for x,e,name,distance in [(46,1,'Крупное препятствие','98,7 м'),(343,9,'Низкое препятствие<br/>поперёк пути','99,4 м'),(640,10,'Тонкий подвешенный<br/>предмет','72,6 м')]:
 para(name,x,135,274,17,PURPLE,bold=True,leading=21)
 para(distance,x,184,274,23,PURPLE,bold=True)
 pic(f'E{e}',x-4,219,282,340)
line(46,570,914)
para('<font color="#ce2871">● Малиновые точки</font>: объект по сохранённой разметке. <font color="#936615">★ Золотая звезда</font>: выбранная точка детектора.',46,581,868,12)
para('Разметка поясняет пример и не является сегментацией алгоритма. Расстояния заданы вдоль номинальной продольной оси, не по криволинейному пути.',46,605,868,11.5,MUTED,leading=15)
c.showPage()
# 3. Реализованные связи.
page(3,'Алгоритм');title('Как работает алгоритм')
para('Геометрия рельсов и дополнительный лучевой признак формируют общий результат',46,102,868,16)
pic('algorithm',46,147,868,273)
para('Ближняя зона',46,437,420,17,PURPLE,bold=True)
para('По текущему облаку восстанавливаем рельсы и проверяем попадание точек в габарит. Разреженные наблюдения подтверждаем во времени.',46,469,420,15,leading=22)
para('Дополнительный канал',495,437,419,17,PURPLE,bold=True)
para('Ищем несоответствия калиброванной структуре лучей. Используем этот признак и для поддержки обнаружения при приближении объекта.',495,469,419,15,leading=22)
box(46,574,868,60)
para('Дальний канал использует особенности синтетической вставки. Обнаружение физических объектов на 100 м этим тестом не подтверждено.',62,586,832,14,PURPLE,leading=20)
c.showPage()
# 4. Только итоговая конфигурация.
m=json.loads((A/'final_metrics.json').read_text());runs=m['runs'];pmin=min(x['p95_ms'] for x in runs);pmax=max(x['p95_ms'] for x in runs)
page(4,'Производительность');title('Обработка входного потока')
para('Итоговая конфигурация. Linux ARM64 VM на Apple M4',46,101,868,17)
for x,value,caption in [(46,'10 Гц','частота входного потока'),(343,'500/500','в каждом из 4 запусков'),(640,f'{comma(pmin)}-{comma(pmax)} мс','p95 задержки выдачи результата')]:
 box(x,148,274,105);para(value,x+16,163,244,29,PURPLE,bold=True);para(caption,x+16,214,244,12)
para('Задержка измерена от публикации входа до завершения обработки сообщения в узле.',46,273,868,15)
rows=[[f'Запуск {x["run"]}',f'{x["point_step_bytes"]} байт','500/500',comma(x['p95_ms']),comma(x['max_ms'])] for x in runs]
table(['Запуск','Размер точки','Завершено','p95, мс','Максимум, мс'],rows,46,315,868,[168,174,174,174,178],row_h=36)
para('Максимальная задержка: 151,1 мс. Отдельные сообщения обрабатывались дольше периода 100 мс при потоке 10 Гц.',46,513,868,15,bold=True,leading=22)
para('Это повторные нагрузочные запуски, не 2000 уникальных сцен. AMD64 проверен функционально в эмуляции на M4. Нативный i7-9700E не измерен.',46,573,868,14,MUTED,leading=21)
c.showPage()
# 5. Проверка и интеграция.
page(5,'Результаты и границы');title('Проверка, ограничения и интеграция')
para('Выбранные проверенные наблюдения и контрольные входы',46,92,868,12,MUTED)
rows=[['Ожидалось обнаружение','13 обнаружений из 21','8 без целевого обнаружения'],['Тревоги не ожидалось','2 тревоги из 12','Известные ошибки'],['Полные фоновые входы','4 положительных из 702','Контроль разработки'],['Реальные контрольные входы','0 положительных из 193','Контроль разработки']]
table(['Выборка','Результат','Что учитывать'],rows,46,112,868,[300,280,288],row_h=39)
para('Выборки разработки, не независимый скрытый тест и не общая оценка полноты или частоты ложных тревог. Контроли не являются исчерпывающей разметкой физических сцен.',46,326,868,15,leading=22)
para('Шесть дополнительных неразмеченных кадров остаются неопределёнными и не включаются в успешные обнаружения.',46,386,868,14,MUTED,leading=20)
pic('integration',46,436,868,111)
para('Получатель контролирует свежесть сообщений. Автоматическое торможение и сертификация безопасности не заявляются.',46,559,868,14,leading=21)
para('<link href="ДЕМО.md" color="#673492"><u>Инструкция запуска и интеграции</u></link>&nbsp;&nbsp;&nbsp;&nbsp;<link href="Техническое_приложение.md" color="#673492"><u>Методика, источники и подробные ограничения</u></link>',46,617,868,12)
c.save();print(P)
