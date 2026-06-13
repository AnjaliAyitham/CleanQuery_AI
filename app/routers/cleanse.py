import io

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.services.data_analyzer import run_full_analysis
from app.services.report_generator import generate_pdf_report
from app.utils.file_parser import parse_file

router = APIRouter()


@router.post("/analyze")
async def analyze_file(file: UploadFile = File(...)):
    """
    Full pipeline: parse → clean → analyze → return JSON summary.
    """
    content = await file.read()
    filename = file.filename or "unknown"

    try:
        df = parse_file(filename, content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {e}")

    analysis = run_full_analysis(df)

    return {
        "filename": filename,
        "raw_kpis": analysis["raw_kpis"],
        "clean_kpis": analysis["clean_kpis"],
        "cleaning_log": analysis["cleaning_log"],
        "column_stats": analysis["column_stats"],
        "relationships": {
            "strong_correlations": analysis["relationships"].get("strong_correlations", []),
            "categorical_associations": analysis["relationships"].get("categorical_associations", []),
            "numeric_categorical": analysis["relationships"].get("numeric_categorical", []),
        },
        "insights": analysis["insights"],
    }


@router.post("/report")
async def generate_report(file: UploadFile = File(...)):
    """
    Full pipeline: parse → clean → analyze → generate PDF report.
    Returns the PDF file as a download.
    """
    content = await file.read()
    filename = file.filename or "unknown"

    try:
        df = parse_file(filename, content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {e}")

    analysis = run_full_analysis(df)
    analysis["raw_df"] = df

    pdf_bytes = generate_pdf_report(analysis, filename)

    report_name = f"{filename.rsplit('.', 1)[0]}_report.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{report_name}"'},
    )


@router.post("/clean-export")
async def export_cleaned(file: UploadFile = File(...)):
    """
    Parse → clean → return cleaned CSV.
    """
    content = await file.read()
    filename = file.filename or "unknown"

    try:
        df = parse_file(filename, content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {e}")

    analysis = run_full_analysis(df)
    df_clean = analysis["cleaned_df"]

    buffer = io.StringIO()
    df_clean.to_csv(buffer, index=False)
    buffer.seek(0)

    clean_name = f"{filename.rsplit('.', 1)[0]}_cleaned.csv"
    return StreamingResponse(
        io.BytesIO(buffer.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{clean_name}"'},
    )
