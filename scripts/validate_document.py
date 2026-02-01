#!/usr/bin/env python3
"""
Document Validation Script for NGS
ตรวจสอบความถูกต้องของเอกสารการเงินก่อน Export PDF
"""

import sys
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ValidationError:
    field: str
    expected: str
    actual: str
    severity: str  # 'error' หรือ 'warning'


def validate_receipt(db_path: Path, doc_number: str) -> Tuple[bool, List[ValidationError]]:
    """
    ตรวจสอบความถูกต้องของ Receipt
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # ดึงข้อมูล Receipt
    cursor.execute("""
        SELECT d.*, c.name as customer_name, c.wht_rate as customer_wht_rate
        FROM documents d
        JOIN customers c ON d.customer_id = c.customer_id
        WHERE d.doc_number = ? AND d.doc_type = 'receipt'
    """, (doc_number,))
    
    receipt = cursor.fetchone()
    if not receipt:
        return False, [ValidationError('doc_number', doc_number, 'Not found', 'error')]
    
    # ดึงข้อมูล Invoice ที่อ้างอิง
    inv_number = receipt['reference']
    cursor.execute("""
        SELECT * FROM documents WHERE doc_number = ? AND doc_type = 'invoice'
    """, (inv_number,))
    invoice = cursor.fetchone()
    
    if not invoice:
        errors.append(ValidationError(
            'reference', 
            f'Invoice {inv_number} exists', 
            'Not found', 
            'error'
        ))
    
    # === Validation Rules ===
    
    # 1. ตรวจสอบ VAT 7%
    expected_vat = round(receipt['subtotal'] * 0.07, 2)
    if abs(receipt['vat'] - expected_vat) > 0.01:
        errors.append(ValidationError(
            'vat',
            f'{expected_vat:.2f} (7% of subtotal)',
            f'{receipt["vat"]:.2f}',
            'error'
        ))
    
    # 2. ตรวจสอบ Total = Subtotal + VAT
    expected_total = receipt['subtotal'] + receipt['vat']
    if abs(receipt['total'] - expected_total) > 0.01:
        errors.append(ValidationError(
            'total',
            f'{expected_total:.2f} (subtotal + vat)',
            f'{receipt["total"]:.2f}',
            'error'
        ))
    
    # 3. ตรวจสอบ WHT
    expected_wht = round(receipt['subtotal'] * (receipt['wht_rate'] / 100), 2)
    if abs(receipt['wht'] - expected_wht) > 0.01:
        errors.append(ValidationError(
            'wht',
            f'{expected_wht:.2f} ({receipt["wht_rate"]}% of subtotal)',
            f'{receipt["wht"]:.2f}',
            'error'
        ))
    
    # 4. ตรวจสอบ net_total (กรณีชำระเต็มจำนวน)
    # หากชำระเต็มจำนวน ต้องเท่ากับ total - wht
    expected_net = receipt['total'] - receipt['wht']
    
    if invoice:
        # ตรวจสอบว่าเป็นการชำระเต็มจำนวนหรือแบ่งชำระ
        cursor.execute("""
            SELECT COALESCE(SUM(total), 0) as total_paid
            FROM documents
            WHERE doc_type = 'receipt' AND reference = ? AND status = 'paid'
        """, (inv_number,))
        total_paid = cursor.fetchone()['total_paid']
        
        # ถ้าชำระครบ invoice แล้ว (หรือใบนี้ทำให้ครบ)
        if abs(total_paid - invoice['total']) < 0.01 or \
           abs((total_paid + receipt['total']) - invoice['total']) < 0.01:
            # ชำระเต็มจำนวน - net_total ต้อง = total - wht
            if abs(receipt['net_total'] - expected_net) > 0.01:
                errors.append(ValidationError(
                    'net_total',
                    f'{expected_net:.2f} (total - wht) for full payment',
                    f'{receipt["net_total"]:.2f}',
                    'error'
                ))
        else:
            # แบ่งชำระ - แค่เตือนให้ตรวจสอบ
            if receipt['net_total'] <= 0:
                errors.append(ValidationError(
                    'net_total',
                    f'> 0 for partial payment',
                    f'{receipt["net_total"]:.2f}',
                    'warning'
                ))
    else:
        # ไม่มี invoice อ้างอิง - ตรวจสอบทั่วไป
        if receipt['net_total'] <= 0:
            errors.append(ValidationError(
                'net_total',
                f'{expected_net:.2f} (total - wht)',
                f'{receipt["net_total"]:.2f}',
                'error'
            ))
    
    # 5. ตรวจสอบจำนวนเงินตัวอักษร (ตรวจสอบคร่าวๆว่าไม่ว่าง)
    if not receipt['amount_words'] or receipt['amount_words'].strip() == '':
        errors.append(ValidationError(
            'amount_words',
            'Not empty',
            'Empty',
            'error'
        ))
    
    # 6. ตรวจสอบว่ามี line items
    cursor.execute("""
        SELECT COUNT(*) as count FROM line_items WHERE doc_number = ?
    """, (doc_number,))
    line_count = cursor.fetchone()['count']
    
    if line_count == 0:
        errors.append(ValidationError(
            'line_items',
            'At least 1 item',
            f'{line_count} items',
            'error'
        ))
    
    # 7. ตรวจสอบ line items รวมกันเท่ากับ subtotal
    cursor.execute("""
        SELECT COALESCE(SUM(line_total), 0) as sum_lines
        FROM line_items WHERE doc_number = ?
    """, (doc_number,))
    sum_lines = cursor.fetchone()['sum_lines']
    
    if abs(sum_lines - receipt['subtotal']) > 0.01:
        errors.append(ValidationError(
            'line_items sum',
            f'{receipt["subtotal"]:.2f} (match subtotal)',
            f'{sum_lines:.2f}',
            'error'
        ))
    
    conn.close()
    
    is_valid = len([e for e in errors if e.severity == 'error']) == 0
    return is_valid, errors


def validate_invoice(db_path: Path, doc_number: str) -> Tuple[bool, List[ValidationError]]:
    """ตรวจสอบความถูกต้องของ Invoice"""
    errors = []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT d.*, c.wht_rate as customer_wht_rate
        FROM documents d
        JOIN customers c ON d.customer_id = c.customer_id
        WHERE d.doc_number = ? AND d.doc_type = 'invoice'
    """, (doc_number,))
    
    invoice = cursor.fetchone()
    if not invoice:
        return False, [ValidationError('doc_number', doc_number, 'Not found', 'error')]
    
    # 1. VAT 7%
    expected_vat = round(invoice['subtotal'] * 0.07, 2)
    if abs(invoice['vat'] - expected_vat) > 0.01:
        errors.append(ValidationError('vat', f'{expected_vat:.2f}', f'{invoice["vat"]:.2f}', 'error'))
    
    # 2. Total
    expected_total = invoice['subtotal'] + invoice['vat']
    if abs(invoice['total'] - expected_total) > 0.01:
        errors.append(ValidationError('total', f'{expected_total:.2f}', f'{invoice["total"]:.2f}', 'error'))
    
    # 3. WHT
    expected_wht = round(invoice['subtotal'] * (invoice['wht_rate'] / 100), 2)
    if abs(invoice['wht'] - expected_wht) > 0.01:
        errors.append(ValidationError('wht', f'{expected_wht:.2f}', f'{invoice["wht"]:.2f}', 'error'))
    
    # 4. net_total = total - wht
    expected_net = invoice['total'] - invoice['wht']
    if abs(invoice['net_total'] - expected_net) > 0.01:
        errors.append(ValidationError('net_total', f'{expected_net:.2f}', f'{invoice["net_total"]:.2f}', 'error'))
    
    # 5. amount_words
    if not invoice['amount_words'] or invoice['amount_words'].strip() == '':
        errors.append(ValidationError('amount_words', 'Not empty', 'Empty', 'error'))
    
    conn.close()
    
    is_valid = len([e for e in errors if e.severity == 'error']) == 0
    return is_valid, errors


def print_validation_result(doc_number: str, doc_type: str, is_valid: bool, errors: List[ValidationError]):
    """แสดงผลการตรวจสอบ"""
    print(f"\n{'='*60}")
    print(f"📋 ตรวจสอบเอกสาร: {doc_number} ({doc_type})")
    print('='*60)
    
    if is_valid and not errors:
        print("✅ ผ่านการตรวจสอบทั้งหมด")
    else:
        for error in errors:
            icon = "🔴" if error.severity == 'error' else "🟡"
            print(f"{icon} [{error.severity.upper()}] {error.field}")
            print(f"   ค่าที่คาดหวัง: {error.expected}")
            print(f"   ค่าที่พบ: {error.actual}")
    
    print('='*60)
    return is_valid


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_document.py <doc_number>")
        print("Example: python validate_document.py RC20260009")
        sys.exit(1)
    
    doc_number = sys.argv[1]
    db_path = Path("/Users/ngs/Library/CloudStorage/OneDrive-Personal/obsidian-vault/Scripts/ngs-doc-export/ngs_finance.db")
    
    # ตรวจสอบประเภทเอกสารจาก doc_number
    if doc_number.startswith('RC'):
        doc_type = 'receipt'
        is_valid, errors = validate_receipt(db_path, doc_number)
    elif doc_number.startswith('IV'):
        doc_type = 'invoice'
        is_valid, errors = validate_invoice(db_path, doc_number)
    else:
        print(f"❌ ไม่รองรับเอกสารประเภทนี้: {doc_number}")
        sys.exit(1)
    
    success = print_validation_result(doc_number, doc_type, is_valid, errors)
    
    if not success:
        print("\n⚠️  กรุณาแก้ไขข้อผิดพลาดก่อน Export PDF")
        sys.exit(1)
    else:
        print("\n✅ สามารถ Export PDF ได้")


if __name__ == '__main__':
    main()
