function tidy {
    param(
        [string]$Project
    )

    Push-Location $Project
    try {
        black .
        isort .
    }

    finally {
        Pop-Location
    }
}