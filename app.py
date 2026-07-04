from flask import Flask, render_template, request, jsonify, send_file
import os
import pandas as pd
import barcode
from barcode.writer import ImageWriter
import io
import base64
from datetime import datetime
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from PIL import Image as PILImage

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_barcode_image(ean_number):
    """Generate EAN-13 barcode and return as bytes"""
    try:
        ean_str = str(ean_number).zfill(13)
        ean = barcode.get_barcode_class('ean13')
        barcode_instance = ean(ean_str, writer=ImageWriter())
        
        buffer = io.BytesIO()
        barcode_instance.write(buffer, {
            'module_width': 0.2,
            'module_height': 15.0,
            'font_size': 10,
            'text_distance': 5.0,
            'background': 'white',
            'foreground': 'black'
        })
        buffer.seek(0)
        
        image_bytes = buffer.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        return {
            'bytes': image_bytes,
            'base64': image_base64
        }
        
    except Exception as e:
        print(f"Error generating barcode for {ean_number}: {e}")
        return None

def generate_pdf_with_barcodes(df, barcode_images, output_path):
    """
    Generate PDF with barcode images
    """
    temp_files = []  # Track temp files for cleanup
    
    try:
        print(f"📄 Starting PDF generation...")
        print(f"📊 DataFrame has {len(df)} rows")
        print(f"🖼️ Barcode images: {len(barcode_images)}")
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            alignment=TA_CENTER,
            fontSize=16,
            textColor=colors.HexColor('#0e4b64')
        )
        elements.append(Paragraph("Product Barcodes", title_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Date
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=10,
            textColor=colors.grey
        )
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style))
        elements.append(Spacer(1, 0.3 * inch))
        
        # Create table data
        table_data = []
        
        # Header
        header = ['Product Name', 'Price', 'Discount (50%)', 'EAN-13', 'Barcode']
        table_data.append(header)
        
        # Add rows
        for idx, (_, row) in enumerate(df.iterrows()):
            print(f"Processing row {idx + 1}")
            
            # Create barcode image
            barcode_img = None
            if idx < len(barcode_images) and barcode_images[idx]:
                try:
                    # Save barcode to temp file
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        tmp.write(barcode_images[idx]['bytes'])
                        tmp_path = tmp.name
                        temp_files.append(tmp_path)
                        print(f"✅ Created temp barcode: {tmp_path}")
                    
                    # Create Image object for PDF
                    img = Image(tmp_path, width=1.2*inch, height=0.4*inch)
                    barcode_img = img
                    
                except Exception as e:
                    print(f"❌ Error creating barcode image for row {idx}: {e}")
                    barcode_img = Paragraph("Error", styles['Normal'])
            else:
                barcode_img = Paragraph("No Barcode", styles['Normal'])
            
            # Prepare row
            row_data = [
                Paragraph(str(row['product_name']), styles['Normal']),
                Paragraph(f"${row['product_price']:.2f}", styles['Normal']),
                Paragraph(f"${row['product_after_discount50%']:.2f}", styles['Normal']),
                Paragraph(str(row['productEanNumber']), styles['Normal']),
                barcode_img
            ]
            table_data.append(row_data)
        
        # Create table
        table = Table(table_data, colWidths=[1.8*inch, 0.8*inch, 0.8*inch, 1.2*inch, 1.5*inch])
        
        # Style table
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0e4b64')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (1, 1), (2, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#0e4b64')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))
        
        # Footer
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=8,
            textColor=colors.grey
        )
        elements.append(Paragraph(f"Total Products: {len(df)}", footer_style))
        
        # Build PDF
        print("🔄 Building PDF...")
        doc.build(elements)
        print(f"✅ PDF generated successfully: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up temp files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    print(f"🧹 Cleaned up: {temp_file}")
            except:
                pass

def process_excel_file(file_path):
    """Process the Excel file"""
    try:
        df = pd.read_excel(file_path)
        print(f"✅ Read Excel file: {len(df)} rows")
        print(f"📋 Columns: {df.columns.tolist()}")
        
        required_columns = ['product_name', 'product_price', 'productEanNumber']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return None, None, f"Missing required columns: {', '.join(missing_columns)}"
        
        # Calculate discount
        df['product_after_discount50%'] = (df['product_price'] / 2).round(2)
        
        # Generate barcodes
        barcode_images = []
        barcode_base64_list = []
        
        for idx, ean in enumerate(df['productEanNumber']):
            print(f"🔄 Generating barcode for row {idx+2}: {ean}")
            barcode_data = generate_barcode_image(ean)
            if barcode_data:
                barcode_images.append(barcode_data)
                barcode_base64_list.append(barcode_data['base64'])
                print(f"✅ Generated barcode for {ean}")
            else:
                barcode_images.append(None)
                barcode_base64_list.append(None)
                print(f"❌ Failed to generate barcode for {ean}")
        
        df['Product_BarCode'] = barcode_base64_list
        df['processed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return df, barcode_images, None
        
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        import traceback
        traceback.print_exc()
        return None, None, f"Error processing file: {str(e)}"

@app.route('/')
def index():
    return render_template('uploads.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
    
    if 'uploadedFile' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['uploadedFile']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Only .xlsx and .xls files are allowed'}), 400
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        print(f"✅ Saved uploaded file: {file_path}")
        
        # Process the Excel file
        processed_df, barcode_images, error = process_excel_file(file_path)
        
        if error:
            return jsonify({'success': False, 'error': error}), 400
        
        # Generate PDF with barcodes
        pdf_filename = f"barcodes_{timestamp}.pdf"
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
        
        pdf_generated = generate_pdf_with_barcodes(processed_df, barcode_images, pdf_path)
        
        if not pdf_generated:
            # Check if file was created anyway
            if os.path.exists(pdf_path):
                print(f"✅ PDF file exists despite error: {pdf_path}")
            else:
                return jsonify({'success': False, 'error': 'Failed to generate PDF'}), 500
        
        # Also save Excel file
        excel_filename = f"processed_{timestamp}.xlsx"
        excel_path = os.path.join(app.config['UPLOAD_FOLDER'], excel_filename)
        processed_df.to_excel(excel_path, index=False)
        
        # Prepare preview data
        preview_df = processed_df.copy()
        preview_df['Product_BarCode'] = preview_df['Product_BarCode'].apply(
            lambda x: f'<img src="data:image/png;base64,{x}" style="height:30px;">' if x else 'Failed'
        )
        preview_data = preview_df.head(5).to_dict('records')
        
        return jsonify({
            'success': True,
            'message': f'✅ Successfully processed {len(processed_df)} products!',
            'filename': file.filename,
            'pdf_filename': pdf_filename,
            'excel_filename': excel_filename,
            'row_count': len(processed_df),
            'columns': processed_df.columns.tolist(),
            'preview': preview_data,
            'barcode_count': sum(1 for x in barcode_images if x is not None)
        })
        
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/download/<filetype>/<filename>')
def download_file(filetype, filename):
    """Download processed file (PDF or Excel)"""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f"📥 Downloading: {file_path}")
        
        if os.path.exists(file_path):
            if filetype == 'pdf':
                return send_file(
                    file_path, 
                    as_attachment=True, 
                    download_name=filename,
                    mimetype='application/pdf'
                )
            else:
                return send_file(
                    file_path, 
                    as_attachment=True, 
                    download_name=filename,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
        else:
            print(f"❌ File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        print(f"❌ Download error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
