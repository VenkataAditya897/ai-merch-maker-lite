import express from 'express';
import fetch from 'node-fetch';
import { createCanvas, loadImage } from 'canvas';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.use(express.json({ limit: '10mb' }));

const PORT = 3000;


const TEMPLATES_DIR = path.join(__dirname, 'templates');
const OUTPUT_DIR = path.join(__dirname, 'output');

if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR);
}

app.get('/', (req, res) => {
  res.status(200).send('Mockup server is up and running.');
});

const productConfig = {
  'tshirt': {
    printArea: { x: 0.25, y: 0.35, width: 0.5, height: 0.35 }
  },
  'cup': {
    printArea: { x: 0.18, y: 0.28, width: 0.47, height: 0.54 }
  },
  'cap': {
    printArea: { x: 0.35, y: 0.3, width: 0.3, height: 0.25 }
  }
};


const findTemplatePath = (productType, color) => {
  const normalizedProductType = productType.toLowerCase().replace(/\s/g, '');
  const normalizedColor = color ? `-${color.toLowerCase().replace(/\s/g, '')}` : '';
  let templateFileName = `${normalizedProductType}${normalizedColor}.png`;
  let templateFilePath = path.join(TEMPLATES_DIR, templateFileName);
  if (fs.existsSync(templateFilePath)) {
    return templateFilePath;
  }
  return null;
};

// This function now handles both vertical and horizontal bending.
function drawTransformedDesign(ctx, designImg, printArea, bendStrengthTop, bendStrengthBottom, horizontalBend) {
  const numStrips = 400; // Increased strips for a smoother look
  const stripWidth = printArea.width / numStrips;
  
  for (let i = 0; i < numStrips; i++) {
    const t = i / (numStrips - 1);
    
    // Vertical bend
    const bendStrength = bendStrengthTop * (1 - t) + bendStrengthBottom * t;
    const bendAmplitudeY = printArea.height * bendStrength;
    const curveOffsetY = -(t * t - t) * bendAmplitudeY;
    
    // Horizontal bend
    const bendAmplitudeX = printArea.width * horizontalBend;
    const curveOffsetX = Math.sin(t * Math.PI) * bendAmplitudeX;

    const sourceX = t * designImg.width;
    const sourceY = 0;
    const sourceWidth = designImg.width / numStrips;
    const sourceHeight = designImg.height;

    const x = printArea.x + i * stripWidth + curveOffsetX;
    const y = printArea.y + curveOffsetY;

    ctx.drawImage(
      designImg,
      sourceX,
      sourceY,
      sourceWidth,
      sourceHeight,
      x,
      y,
      stripWidth,
      printArea.height
    );
  }
}

app.post('/mockup', async (req, res) => {
  try {
    const { image_url, product_type, color } = req.body;

    if (!image_url || !product_type || !color) {
      return res.status(400).json({ error: 'Missing image_url, product_type, or color in request body' });
    }

    const templatePath = findTemplatePath(product_type, color);

    if (!templatePath) {
      return res.status(400).json({ error: `No template found for product type "${product_type}" with color "${color}".` });
    }

    const templateConfig = productConfig[product_type.toLowerCase().replace(/\s/g, '')];

    if (!templateConfig) {
      return res.status(400).json({ error: `Product type "${product_type}" is not supported in the configuration.` });
    }

    const templateImg = await loadImage(templatePath);
    let designImg;
    if (image_url.startsWith('http')) {
      const response = await fetch(image_url);
      if (!response.ok) throw new Error('Failed to fetch image from URL');
      const buffer = await response.buffer();
      designImg = await loadImage(buffer);
    } else {
      if (path.isAbsolute(image_url)) {
        designImg = await loadImage(image_url);
      } else {
        designImg = await loadImage(path.resolve(__dirname, image_url));
      }

    }

    const canvas = createCanvas(templateImg.width, templateImg.height);
    const ctx = canvas.getContext('2d');
    
    ctx.drawImage(templateImg, 0, 0);

    const printArea = templateConfig.printArea;
    const printAreaWidth = templateImg.width * printArea.width;
    const printAreaHeight = templateImg.height * printArea.height;
    const printAreaX = templateImg.width * printArea.x;
    const printAreaY = templateImg.height * printArea.y;

    const designAspectRatio = designImg.width / designImg.height;
    const printAreaAspectRatio = printAreaWidth / printAreaHeight;

    let finalDesignWidth, finalDesignHeight;
    if (designAspectRatio > printAreaAspectRatio) {
      finalDesignWidth = printAreaWidth;
      finalDesignHeight = finalDesignWidth / designAspectRatio;
    } else {
      finalDesignHeight = printAreaHeight;
      finalDesignWidth = finalDesignHeight * designAspectRatio;
    }

    const finalDesignX = printAreaX + (printAreaWidth - finalDesignWidth) / 2;
    const finalDesignY = printAreaY + (printAreaHeight - finalDesignHeight) / 2;

    if (product_type.toLowerCase() === 'cup') {
      const curvedPrintArea = {
        x: finalDesignX,
        y: finalDesignY,
        width: finalDesignWidth,
        height: finalDesignHeight
      };
      // For cups, use a symmetrical vertical curve.
      drawTransformedDesign(ctx, designImg, curvedPrintArea, 0.13, 0.15, 0);
    } else if (product_type.toLowerCase() === 'cap') {
      const curvedPrintArea = {
        x: finalDesignX,
        y: finalDesignY,
        width: finalDesignWidth,
        height: finalDesignHeight
      };
      // Horizontal and vertical bend for the cap's rounded shape.
      drawTransformedDesign(ctx, designImg, curvedPrintArea, 0.05, 0.05, 0); 
    } else {
      ctx.globalAlpha = 0.95;
      ctx.drawImage(designImg, finalDesignX, finalDesignY, finalDesignWidth, finalDesignHeight);
      ctx.globalAlpha = 1.0;
    }
    
    const timestamp = Date.now();
    const outputFilename = `mockup_${timestamp}.png`;
    const outputPath = path.join(OUTPUT_DIR, outputFilename);

    const outStream = fs.createWriteStream(outputPath);
    const stream = canvas.createPNGStream();
    stream.pipe(outStream);

    outStream.on('finish', () => {
      const mockupResponse = {
        mockup_id: `mockup_${timestamp}`,
        mockup_url: `http://localhost:${PORT}/output/${outputFilename}`,
        product_type: product_type,
        color: color
      };
      return res.json(mockupResponse);
    });

  } catch (error) {
    console.error('Error in /mockup:', error);
    return res.status(500).json({ error: error.message });
  }
});

app.use('/output', express.static(path.join(__dirname, 'output')));

app.listen(PORT, () => {
  console.log(`Mockup visualizer running on http://localhost:${PORT}`);
});