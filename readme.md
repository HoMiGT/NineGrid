# nine_grid
九宫格图片拼接

简单使用
```
python nine_grid.py 1.jpg 2.jpg 3.jpg 4.jpg 5.jpg 6.jpg 7.jpg 8.jpg 9.jpg -r 1.jpg -s imgs -o result.jpg
```

帮助信息
```
python nine_grid.py --help                                                                                                                        
usage: nine_grid.py [-h] [-s SOURCE] [-o OUTPUT] [-r 序号或文件名] [--crop-x CROP_X] [--crop-y CROP_Y] [--crop 序号:X,Y] [--gap GAP] [--border BORDER] [--background BACKGROUND]  
                    [--quality 1-100]
                    [images ...]

把 9 张图片合成为 3x3 九宫格。默认自动计算合适的正方形单格尺寸；尺寸不足的图片会先等比放大，再从每张图片各自的指定坐标开始裁剪。

positional arguments:
  images                按排列顺序提供 9 张图片；使用 --source 且目录内正好有 9 张时可省略

options:
  -h, --help            show this help message and exit
  -s, --source SOURCE   图片源目录；未提供图片名时，自动读取目录内的 9 张图片
  -o, --output OUTPUT   输出文件，默认 nine_grid.jpg
  -r, --reference 序号或文件名
                        指定标准尺寸图片，可填写 1-9 的图片序号或文件名/路径；例如 -r 3 或 -r 3.jpg；省略时自动计算正方形尺寸
  --crop-x CROP_X       裁剪起点 X，默认 0
  --crop-y CROP_Y       裁剪起点 Y，默认 0
  --crop 序号:X,Y         单独设置某张图片的裁剪起点，可重复使用；例如 --crop 2:30,10 --crop 5:0,80。未指定时使用全局起点
  --gap GAP             图片间隙像素；默认约为单格短边的 2.5%
  --border BORDER       大图外边框像素；默认约为单格短边的 6%
  --background BACKGROUND
                        间隙和边框颜色，默认 #FFFFFF
  --quality 1-100       JPEG质量，默认95
```

python nine_grid.py 1.jpg 2.jpg 3.jpg 4.jpg 5.jpg 6.jpg 7.jpg 8.jpg 9.jpg  -s imgs -o result.jpg --crop 2:0,1000 --crop 3:1100,0 --crop 4:0,1200 --crop 5:510,25 --crop 6:2500,1500 --crop 7:0,1000 --crop 8:1000,1200 --crop 9:0,1000

python nine_grid.py 2.jpg 3.jpg 4.jpg 1.jpg 5.jpg 7.jpg 6.jpg 8.jpg 9.jpg -s imgs -o result1.jpg --crop 1:0,1000 --crop 2:1100,0 --crop 3:0,1200 --crop 5:510,25 --crop 6:0,1000 --crop 7:2500,1500 --crop 8:1000,1200 --crop 9:0,1000



