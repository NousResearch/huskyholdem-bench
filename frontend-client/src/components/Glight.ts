export class Glitch {
  private channelLen = 4;
  private imgOrigin: any;
  private copyData: Uint8ClampedArray = new Uint8ClampedArray(0);
  private flowLineImgs: any[] = [];
  private shiftLineImgs: (Uint8ClampedArray | null)[] = [];
  private shiftRGBs: (Uint8ClampedArray | null)[] = [];
  private scatImgs: { img: any; x: number; y: number }[] = [];
  private throughFlag = true;

  constructor(img: any, private p5: any) {
    this.imgOrigin = img;
    this.imgOrigin.loadPixels();
    this.copyData = new Uint8ClampedArray(this.imgOrigin.pixels);

    for (let i = 0; i < 1; i++) {
      this.flowLineImgs.push({
        pixels: null,
        t1: this.p5.floor(this.p5.random(0, 1000)),
        speed: this.p5.floor(this.p5.random(4, 24)),
        randX: this.p5.floor(this.p5.random(24, 80)),
      });
    }

    for (let i = 0; i < 6; i++) this.shiftLineImgs.push(null);
    for (let i = 0; i < 1; i++) this.shiftRGBs.push(null);
    for (let i = 0; i < 3; i++) this.scatImgs.push({ img: null, x: 0, y: 0 });
  }

  private replaceData(destImg: any, srcPixels: Uint8ClampedArray) {
    for (let y = 0; y < destImg.height; y++) {
      for (let x = 0; x < destImg.width; x++) {
        const i = (y * destImg.width + x) * this.channelLen;
        destImg.pixels[i] = srcPixels[i];
        destImg.pixels[i + 1] = srcPixels[i + 1];
        destImg.pixels[i + 2] = srcPixels[i + 2];
        destImg.pixels[i + 3] = srcPixels[i + 3];
      }
    }
    destImg.updatePixels();
  }

  private flowLine(srcImg: any, obj: any) {
    const destPixels = new Uint8ClampedArray(srcImg.pixels);
    obj.t1 %= srcImg.height;
    obj.t1 += obj.speed;
    const tempY = this.p5.floor(obj.t1);
    for (let y = 0; y < srcImg.height; y++) {
      if (tempY === y) {
        for (let x = 0; x < srcImg.width; x++) {
          const i = (y * srcImg.width + x) * this.channelLen;
          destPixels[i] = srcImg.pixels[i] + obj.randX;
          destPixels[i + 1] = srcImg.pixels[i + 1] + obj.randX;
          destPixels[i + 2] = srcImg.pixels[i + 2] + obj.randX;
          destPixels[i + 3] = srcImg.pixels[i + 3];
        }
      }
    }
    return destPixels;
  }

  private shiftLine(srcImg: any) {
    const destPixels = new Uint8ClampedArray(srcImg.pixels);
    const rangeMin = this.p5.floor(this.p5.random(0, srcImg.height));
    const rangeMax = rangeMin + this.p5.floor(this.p5.random(1, srcImg.height - rangeMin));
    const offsetX = this.channelLen * this.p5.floor(this.p5.random(-40, 40));

    for (let y = 0; y < srcImg.height; y++) {
      if (y > rangeMin && y < rangeMax) {
        for (let x = 0; x < srcImg.width; x++) {
          const i = (y * srcImg.width + x) * this.channelLen;
          const r2 = (i + offsetX) % srcImg.pixels.length;
          destPixels[i] = srcImg.pixels[r2];
          destPixels[i + 1] = srcImg.pixels[(i + 1 + offsetX) % srcImg.pixels.length];
          destPixels[i + 2] = srcImg.pixels[(i + 2 + offsetX) % srcImg.pixels.length];
          destPixels[i + 3] = srcImg.pixels[i + 3];
        }
      }
    }
    return destPixels;
  }

  private shiftRGB(srcImg: any) {
    const destPixels = new Uint8ClampedArray(srcImg.pixels);
    const range = 16;
    const randR = (this.p5.floor(this.p5.random(-range, range)) * srcImg.width +
      this.p5.floor(this.p5.random(-range, range))) * this.channelLen;
    const randG = (this.p5.floor(this.p5.random(-range, range)) * srcImg.width +
      this.p5.floor(this.p5.random(-range, range))) * this.channelLen;
    const randB = (this.p5.floor(this.p5.random(-range, range)) * srcImg.width +
      this.p5.floor(this.p5.random(-range, range))) * this.channelLen;

    for (let y = 0; y < srcImg.height; y++) {
      for (let x = 0; x < srcImg.width; x++) {
        const i = (y * srcImg.width + x) * this.channelLen;
        destPixels[i] = srcImg.pixels[(i + randR) % srcImg.pixels.length];
        destPixels[i + 1] = srcImg.pixels[(i + 1 + randG) % srcImg.pixels.length];
        destPixels[i + 2] = srcImg.pixels[(i + 2 + randB) % srcImg.pixels.length];
        destPixels[i + 3] = srcImg.pixels[i + 3];
      }
    }
    return destPixels;
  }

  private getRandomRectImg(srcImg: any) {
    const startX = this.p5.floor(this.p5.random(0, srcImg.width - 30));
    const startY = this.p5.floor(this.p5.random(0, srcImg.height - 50));
    const rectW = this.p5.floor(this.p5.random(30, srcImg.width - startX));
    const rectH = this.p5.floor(this.p5.random(1, 50));
    const destImg = srcImg.get(startX, startY, rectW, rectH);
    destImg.loadPixels();
    return destImg;
  }

  public show() {
    const p5 = this.p5;

    this.replaceData(this.imgOrigin, this.copyData);

    const n = p5.floor(p5.random(100));
    if (n > 75 && this.throughFlag) {
      this.throughFlag = false;
      setTimeout(() => {
        this.throughFlag = true;
      }, p5.floor(p5.random(40, 400)));
    }

    if (!this.throughFlag) {
      p5.push();
      p5.translate((p5.width - this.imgOrigin.width) / 2, (p5.height - this.imgOrigin.height) / 2);
      p5.image(this.imgOrigin, 0, 0);
      p5.pop();
      return;
    }

    this.flowLineImgs.forEach((v, i, arr) => {
      arr[i].pixels = this.flowLine(this.imgOrigin, v);
      if (arr[i].pixels) {
        this.replaceData(this.imgOrigin, arr[i].pixels);
      }
    });

    this.shiftLineImgs.forEach((_, i, arr) => {
      if (p5.floor(p5.random(100)) > 50) {
        arr[i] = this.shiftLine(this.imgOrigin);
        this.replaceData(this.imgOrigin, arr[i]!);
      } else if (arr[i]) {
        this.replaceData(this.imgOrigin, arr[i]!);
      }
    });

    this.shiftRGBs.forEach((_, i, arr) => {
      if (p5.floor(p5.random(100)) > 65) {
        arr[i] = this.shiftRGB(this.imgOrigin);
        this.replaceData(this.imgOrigin, arr[i]!);
      }
    });

    p5.push();
    p5.translate((p5.width - this.imgOrigin.width) / 2, (p5.height - this.imgOrigin.height) / 2);
    p5.image(this.imgOrigin, 0, 0);
    p5.pop();

    this.scatImgs.forEach((obj) => {
      p5.push();
      p5.translate((p5.width - this.imgOrigin.width) / 2, (p5.height - this.imgOrigin.height) / 2);
      if (p5.floor(p5.random(100)) > 80) {
        obj.x = p5.floor(p5.random(-this.imgOrigin.width * 0.3, this.imgOrigin.width * 0.7));
        obj.y = p5.floor(p5.random(-this.imgOrigin.height * 0.1, this.imgOrigin.height));
        obj.img = this.getRandomRectImg(this.imgOrigin);
      }
      if (obj.img) {
        p5.image(obj.img, obj.x, obj.y);
      }
      p5.pop();
    });
  }
}
