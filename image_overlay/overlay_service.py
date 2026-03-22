import io
from rembg import remove
from PIL import Image

def process_car_overlay(car_image_path, background_image_path, output_path, position_y_offset=0):
    """
    Entfernt den Hintergrund eines Fahrzeugs und platziert es in Originalgröße auf einem neuen Hintergrund.
    Das Auto wird unten mittig platziert.

    :param car_image_path: Pfad zum Bild mit dem Auto (z.B. auto.jpg)
    :param background_image_path: Pfad zum neuen Hintergrundbild (z.B. hof.jpg)
    :param output_path: Speicherort des Ergebnisses (z.B. ergebnis.jpg)
    :param position_y_offset: Verschiebung nach oben (negativ) oder unten (positiv) in Pixeln, 
                             um das Auto feinjustiert auf die Straße zu setzen.
    """
    
    print(f"Lade Fahrzeugbild: {car_image_path}...")
    with open(car_image_path, 'rb') as i:
        input_image = i.read()
        # 1. Fahrzeug-Hintergrund entfernen
        print("Entferne Hintergrund vom Fahrzeug (das kann einen Moment dauern)...")
        car_no_bg_data = remove(input_image)
        print("Hintergrund erfolgreich entfernt.")

    # Das freigestellte Auto als PIL Image öffnen und in RGBA konvertieren
    car_img = Image.open(io.BytesIO(car_no_bg_data)).convert("RGBA")
    car_w, car_h = car_img.size
    
    # 2. Hintergrund laden
    print(f"Lade Hintergrundbild: {background_image_path}...")
    background_img = Image.open(background_image_path).convert("RGBA")
    bg_w, bg_h = background_img.size

    # 3. Skalierung (Wie gewünscht: Keine Skalierung, Originalgröße beibehalten)
    # car_resized = car_img  # Wir verwenden car_img direkt

    # 4. Positionierung (Mittig im unteren Bereich)
    # Berechne X-Position für die Mitte
    pos_x = (bg_w - car_w) // 2
    
    # Berechne Y-Position für den unteren Rand (mit Offset)
    # Das Auto wird so platziert, dass seine Unterkante am unteren Rand des Hintergrunds liegt.
    pos_y = (bg_h - car_h) + position_y_offset
    
    print(f"Platziere Auto bei Position: X={pos_x}, Y={pos_y}")

    # 5. Zusammenfügen
    # Das Fahrzeug wird mit seinem Alpha-Kanal (Transparenz) auf den Hintergrund gelegt
    print("Füge Bilder zusammen...")
    # Erstelle eine Kopie des Hintergrunds, um das Original nicht zu verändern
    result_img = background_img.copy()
    result_img.paste(car_img, (pos_x, pos_y), car_img)
    
    # 6. Speichern (als RGB, da JPEG keine Transparenz unterstützt)
    print(f"Speichere Ergebnis unter: {output_path}...")
    final_img = result_img.convert("RGB")
    final_img.save(output_path, "JPEG", quality=95)
    print("Fertig!")
    return output_path

# Beispielaufruf
if __name__ == "__main__":
    # HIER DIE PFADE ANPASSEN, WENN DIE DATEIEN ANDERS HEISSEN ODER WOANDERS LIEGEN
    car_file = "car.jpg" # Placeholder
    bg_file = "fixed_background.png"
    output_file = "result.jpg"

    process_car_overlay(
        car_image_path=car_file,
        background_image_path=bg_file,
        output_path=output_file,
        position_y_offset=0  
    )
