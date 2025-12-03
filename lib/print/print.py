import os
import PIL.FontFile
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont

from typing import Iterable, List

PRINT_DPI = 600
# PRINT_DPI = 300
# PRINT_DPI = 150
# PRINT_DPI = 96
# PRINT_DPI = 64
# PRINT_DPI = 32

# 72
def font_to_pt(pt):
    return int((pt/72)*PRINT_DPI)

RES_DIR = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), 'resources')


class Fonts:
    FONTS_DIR: str = os.path.join(RES_DIR, 'fonts')

    @staticmethod
    def open(fontname, size=10) -> PIL.ImageFont.FreeTypeFont:
        return PIL.ImageFont.truetype(os.path.join(Fonts.FONTS_DIR, fontname), size=size)

    class _Font:
        def __init__(self, name) -> None:
            self._name = f"{name}.ttf"

        def __call__(self, size=10) -> PIL.ImageFont.FreeTypeFont:
            return Fonts.open(self._name, size)

        def __str__(self) -> str:
            return self._name

        def __repr__(self) -> str:
            return f'{self.__class__.__name__}({self._name})'

    Arial_Bold_Italic = _Font('Arial_Bold_Italic')
    Arial_Bold = _Font('Arial_Bold')
    Arial_Italic = _Font('Arial_Italic')
    Arial = _Font('Arial')
    Courier_New = _Font('Courier_New')
    Verdana_Bold_Italic = _Font('Verdana_Bold_Italic')
    Verdana_Bold = _Font('Verdana_Bold')
    Verdana_Italic = _Font('Verdana_Italic')
    Verdana = _Font('Verdana')

    @classmethod
    def fonts(cls) -> Iterable['Fonts._Font']:
        for val in cls.__dict__.values():
            if isinstance(val, Fonts._Font):
                yield val

def in_to_mm(inches: float) -> float:
    return inches * 25.4


def mm_to_in(mm: float) -> float:
    return mm / 25.4


def in_to_pt(inches: float) -> int:
    return int(inches * PRINT_DPI)


def mm_to_pt(mm: float) -> int:
    return in_to_pt(mm_to_in(mm))


def pt_to_in(pt: int) -> float:
    return pt / PRINT_DPI


def pt_to_mm(pt: int) -> float:
    return in_to_mm(pt_to_in(pt))


def scale(orig_size: tuple, new_size: tuple) -> tuple:
    orig_ratio = orig_size[0] / orig_size[1]
    new_ratio = new_size[0] / new_size[1]
    if orig_ratio > new_ratio:
        return (new_size[0], int(new_size[0] / orig_ratio))
    else:
        return (int(new_size[1] * orig_ratio), new_size[1])


def resize_cover(image: PIL.Image.Image, size: tuple) -> PIL.Image.Image:
    """Resize an image to cover the target size, maintaining aspect ratio."""
    # """
    # 10x20 >    100x100 
    # 10x20 > 100x200 > 100x100
    
    # 10x20 >> 200x100
    # 10x20 > 200x400 > 200x100
    
    # 20x10 >> 100x100
    # 20x10 > 200x100 > 100x100

    # 20x10 >> 100x200
    # 20x10 > 

    # 100x80 >> 150x75
    # 100x80 > 150x120 > 150x7511
    # """
    width, height = image.size
    orig_ratio = width / height

    target_width, target_height = size

    # Determine which dimension to scale
    if orig_ratio > 1:
        new_width = target_width
        new_height = int(target_width/orig_ratio)
    else:
        new_height = target_height
        new_width = int(target_height * orig_ratio)

    # Resize and crop
    resized_image = image.resize(
        (new_width, new_height), PIL.Image.Resampling.LANCZOS)
    x_offset = (new_width - target_width) // 2
    y_offset = (new_height - target_height) // 2
    cropped_image = resized_image.crop(
        (x_offset, y_offset, x_offset + target_width, y_offset + target_height))
 
    return cropped_image


def center(left, top, right, bottom) -> tuple:
    return (int((left + right)/2), int((top+bottom)/2))


def getbbox(text: str, font: PIL.ImageFont.FreeTypeFont):
    width = 0
    height = 0

    for line in text.split('\n'):
        left, top, right, bottom = font.getbbox(line)
        w = right - left
        h = bottom - top
        if w > width:
            width = w
        height += h
    return (0, 0, width, height)


def tuple_int(*args):
    items = []
    for i in args:
        items.append(int(i))
    return tuple(items)

class Element:
    def __init__(self, position: tuple, size: tuple):
        self._pos = position
        self._size = size

    @property
    def box(self):
        x, y = self.position
        w, h = self.size
        return tuple_int(x, y, x + w, y + h)

    @property
    def position(self):
        return tuple_int(*self._pos)

    @property
    def size(self):
        return tuple_int(*self._size)

    def draw(self, image: PIL.Image.Image):
        pass


class Image(Element):
    def __init__(self, image: str, *, pos:tuple=None, size:tuple=None,  box: tuple = None):
        self._image: PIL.Image.Image = PIL.Image.open(image)

        pos = pos if pos else (0, 0)
        size = size if size else (self._image.width, self._image.height)
        if box:
            if len(box) >= 2:
                pos = (box[0], box[1])
            if len(box) == 4:
                size = (box[2]-box[0], box[3]-box[1])
        
        super().__init__(pos, size)

    def draw(self, image: PIL.Image.Image):
        img = resize_cover(self._image, self.size)
        image.paste(img, self.position)


class Text(Element):
    def __init__(self, text: str, size: int = 12, box: tuple = (0, 0), color: str = 'black', anchor='lt'):
        self._font: PIL.ImageFont.FreeTypeFont = Fonts.Arial_Bold(size)
        self._text = text
        self._color = color
        self._hanchor = anchor[0]
        self._vanchor = anchor[1]

        pos = (0, 0)
        size = (0, 0)
        if box and len(box) >= 2:
            pos = (box[0], box[1])
        if box and len(box) == 4:
            size = (box[2]-box[0], box[3]-box[1])

        super().__init__(pos, size)

    @property
    def anchor(self) -> str:
        v = self._vanchor
        if v == 't':
            v = 'a'
        elif v == 'b':
            v = 'd'
        return ''.join([self._hanchor, v])

    def get_align(self):
        if self._hanchor == 'l':
            return 'left'
        elif self._hanchor == 'm':
            return 'center'
        elif self._hanchor == 'r':
            return 'right'
        return 'left'

    def get_xy(self):
        x, y = self.size
        if x == 0 and y == 0:
            return self.position

        x, y = self.position
        left, top, right, bottom = self.box
        # print(self.box)
        if self._hanchor == 'l':
            x = left
        elif self._hanchor == 'm':
            x = int(left+(right-left)/2)
        elif self._hanchor == 'r':
            x = right

        if self._vanchor in 'ta':
            y = top
        elif self._vanchor == 'm':
            y = int(top+(bottom-top)/2)
        elif self._vanchor in 'bd':
            y = bottom
        return (x, y)

    def draw(self, image: PIL.Image.Image):
        draw = PIL.ImageDraw.Draw(image)
        align = self.get_align()
        xy = self.get_xy()

        draw.text(xy, self._text, fill=self._color,
                  font=self._font,  anchor=self.anchor, align=align)


class Rect(Element):
    def __init__(self, position, size, fill=None, outline=None, width=1):
        super().__init__(position, size)
        self._fill = fill
        self._outline = outline
        self._width = width
    
    def draw(self, image):
        draw = PIL.ImageDraw.Draw(image)
        draw.rectangle(self.box, fill=self._fill, outline=self._outline, width=self._width)


class Page:
    def __init__(self, width_in: int, height_in: int):
        self._size = (in_to_pt(width_in), in_to_pt(height_in))
        self._elements : List[Element] = []
    @property
    def width(self) -> int:
        return int(self._size[0])

    @width.setter
    def width(self, val: int):
        self._size = (val, self._size[1])

    @property
    def height(self) -> int:
        return int(self._size[1])

    @height.setter
    def height(self, val: int):
        self._size = (self._size[0], val)

    def add_element(self, element:Element):
        self._elements.append(element)

    def to_image(self):
        img = PIL.Image.new('RGBA', self._size, color='white')
        for element in self._elements:
            element.draw(img)
        return img


class LetterPage(Page):
    def __init__(self):
        super().__init__(11, 8.5)


class FrontPage(LetterPage):
    """
    Letter Size: 11in x 8.5in (215.9 millimeters by 279.4mm 215.9mm))

    Front Page:
    - Padding: 10mm
    - Margin: 5mm
    - Image: 165mmx279.4mm
    - Text: 50mmx279.4mm
    """
    TOP_PADDING = mm_to_pt(10)
    IMG_MARGIN = mm_to_pt(5)
    IMG_SIZE = (mm_to_pt(279.4), mm_to_pt(165))

    def __init__(self, image: str, text: str):
        super().__init__()
        self._image = image
        self._text = text
        self.load()

    def load(self):
        # Add black background
        y_pos = self.TOP_PADDING
        pos = (0, y_pos)
        size = (self.width, self.height)
        self.add_element(Rect(pos, size, fill='black'))

        # Add Image
        y_pos += self.IMG_MARGIN
        pos = (0, y_pos)
        size = self.IMG_SIZE
        self.add_element(Image(self._image, pos=pos, size=size))
        y_pos += self.IMG_SIZE[1]
        # Add Title
        y_pos += mm_to_pt(2)
        box = (0, y_pos, self.width, self.height)

        self.add_element(Text(self._text, size=font_to_pt(24), box=box, color='white', anchor='mt'))

    # def to_image(self):
    #     # New Page Letter landscape
    #     img = PIL.Image.new('RGB', self._size, color='black')
    #     y_pos = 0
    #     if True:
    #         # 10mm top padding
    #         draw = PIL.ImageDraw.Draw(img)
    #         draw.rectangle([0, y_pos, self.width, y_pos +
    #                        self.TOP_PADDING], fill='white')
    #         y_pos += FrontPage.TOP_PADDING
    #     if self._image:
    #         # 5mm margin
    #         y_pos += FrontPage.IMG_MARGIN
    #         # Draw Image
    #         image: PIL.Image.Image = PIL.Image.open(self._image)
    #         image = resize_cover(image, self.IMG_SIZE)
    #         img.paste(image, (0, y_pos))
    #         y_pos += self.IMG_SIZE[1]

    #     if self._text:
    #         # Draw Title
    #         draw = PIL.ImageDraw.Draw(img)
    #         # X center possiont
    #         x_pos = int(self.width/2)
    #         # Add 5mm padding
    #         y_pos += mm_to_pt(1)
    #         font = Fonts.Arial_Bold(mm_to_pt(10))
    #         draw.text(xy=(x_pos, y_pos), text=self._text, font=font,
    #                   fill='white', anchor='ma', align='center')

    #     img.save('out/front_page.png')
    #     return img


class ArtPage(LetterPage):
    BIND_PADDING = mm_to_pt(10)
    BORDER = in_to_pt(.5)

    def __init__(self, image: str = None, text: str = None):
        super().__init__()
        self._image = image
        self._text = text
        self.load()

    def load(self):
        # Black Background
        pos = (0,0)
        size = (self.width, self.height-self.BIND_PADDING)
        self.add_element(Rect(pos, size, fill='black'))
        
        # Add Photo
        pos = (self.BORDER, self.BORDER*1.5)
        size = (self.width-pos[0]*2, self.height-pos[1]*2-self.BIND_PADDING)
        img = Image(self._image, pos=pos, size=size)
        self.add_element(img)

        box = img.box
        # Add description
        pos = (box[0], box[3]+mm_to_pt(2))
        self.add_element(Text(self._text, box=pos, size=font_to_pt(12), color='white'))


def bbox(pos, size):
    return (pos[0], pos[1], size[0]+pos[0], size[1]+pos[1])

class PrintDecoder:
    def __init__(self):
        self._handlers = {}
    
    def draw(self, obj) -> PIL.Image:
        type_ = type(obj)
        ret = None
        if type_ in self._handlers:
            ret = self._handlers[type_](obj)
        elif hasattr(obj, '__draw__'):
            ret = obj.__draw__()
        else:
            raise ValueError(f"Unsuported Type {type_}")
        return ret    

    def override(self, _type:type):
        def handler(func):
            self._handlers[_type] = func
            return func
        return handler

if __name__ == "__main__":
    
    # img = PIL.Image.new('RGB', (300, 500), color='white')
    
    # draw = PIL.ImageDraw.Draw(img)
    
    # pos = 10
    # for h in ['l', 'm', 'r']:
    #     for v in ['t', 'm', 'b']:
    #         anchor = ''.join([h,v])
    #         # print(anchor)
    #         _bbox = bbox((10,pos),(200,30))
    #         pos += 50
    #         draw.rectangle(_bbox, outline='red')
    #         t = Text(f"Test {anchor}", box=_bbox, anchor=anchor, color='red')
    #         t.draw(img)
    # _bbox = bbox((10,50),(200,30))
    # draw.rectangle(_bbox, outline='red')
    # t = Text("Test 2", box=_bbox, anchor='lm', color='green')
    # t.draw(img)
    # _bbox = bbox((10,100),(200,30))
    # draw.rectangle(_bbox, outline='red')
    # t = Text("Test 3", box=_bbox, anchor='lb', color='blue')
    # t.draw(img)
    
    # img.show()
    # pass
    # txt1 = "Hello World"
    # txt2 = "Hello\nWorld"
    # txt3 = "1234\n12345\n123456789"
    # font = Fonts.Arial(12)

    # print(getbbox(txt1, font))
    # print(getbbox(txt2, font))
    # print(getbbox(txt3, font))
    front_page = FrontPage('resources/images/PXL_COVER.jpg', 'CALENDAR\n2025')
    img = front_page.to_image()
    img.show()

    art_page = ArtPage('resources/images/PXL_COVER.jpg', 'This is a Sample Text\nSome Location, TX Jan 2025')
    img = art_page.to_image()
    img.show()
    img.save("test.png")
