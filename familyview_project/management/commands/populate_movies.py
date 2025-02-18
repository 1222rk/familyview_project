import os
from openpyxl import load_workbook
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

from familyview_project.models import Movie

class Command(BaseCommand):
    help = 'Load movie data from Excel file (fyp_dataset.xlsx) using openpyxl'

    def handle(self, *args, **options):
        # 1. Build path to your XLSX file in familyview_project/data
        file_path = os.path.join(settings.BASE_DIR, 'familyview_project', 'data', 'fyp_dataset.xlsx')

        # 2. Load the workbook and select the desired sheet
        wb = load_workbook(filename=file_path)
        ws = wb.active  # or wb['SheetName'] if you have a named sheet

        # 3. Use a database transaction for all inserts/updates
        with transaction.atomic():
            row_count = 0

            # 4. Iterate over rows, skipping header (min_row=2)
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or len(row) < 4:
                    # e.g. if your columns are Title, Genre, Release Date, Age Rating
                    continue

                # Unpack columns
                title = row[0]         # e.g. "The Dark Knight"
                genre = row[1]         # e.g. "Action"
                release_date = row[2]  # e.g. "2008" or "1957 U"
                age_rating = row[3]    # e.g. "U", "PG", "12", or "15"

                # Skip if no title
                if not title:
                    print(f"Skipping row due to missing title: {row}")
                    continue

                # Handle age_rating if you have choices
                valid_ratings = ["U", "PG", "12"]
                if age_rating not in valid_ratings:
                    age_rating = "12"

                # 5. Create or update Movie
                Movie.objects.update_or_create(
                    title=title,
                    defaults={
                        'genre': genre or '',  # fallback if None
                        'release_date': str(release_date) if release_date else '',
                        'age_rating': age_rating,
                    }
                )
                row_count += 1

        print(f'Data import complete. Processed {row_count} rows.')
