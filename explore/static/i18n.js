/* All interface text lives here. Keep scientific interpretations parallel in EN/NL. */
window.EASE_I18N = {
  en: {
    hostPublic: "Public demo",
    hostDemoHint: "Explore two saved calculations on public Rijkswaterstaat bathymetry with an assumed design at −6.50 m NAP.",
    hostLoad: "Open demo result",
    hostLab: "Connect to the analysis server",
    hostPrivacy: "Survey files are processed on the project server. Original files are removed after processing. Download results before they expire, up to one hour after calculation. Upload only approved files.",
    hostKey: "Project access key",
    hostUnlock: "Connect",
    hostLock: "Disconnect and clear workspace",
    hostChecking: "Checking server access…",
    hostUnlocked: "Connected. You can now inspect or analyse a survey.",
    hostDemoReady: "The public example uses fixed inputs. Connect to run a new calculation.",
    hostDemoOnly: "The public example uses fixed inputs. Use the local application to analyse new surveys.",
    hostDemoError: "The demo could not load. Refresh and try again.",
    hostOffline: "The analysis server is unavailable. Try again in a minute or open the public demo.",
    hostExpired: "This download has expired. Run the analysis again.",
    hostDownloadError: "The file could not be downloaded. Check your access and try again.",

    pageTitle: 'EASE · Sediment volume explorer', brandSub: 'Waterway insight, made clear', language: 'Interface language',
    local: 'Local prototype', eyebrow: 'SURVEY → SURFACE → VOLUME', title: 'Understand what lies above the reference.',
    intro: 'Compare a measured waterbed with a defined reference. Explore the surface, review the coverage, and export an explainable volume calculation.',
    setup: 'Set up your analysis', setupSub: 'Georeferenced measurements in. A transparent comparison out.',
    demo: 'Load Dutch bathymetry', demoHint: 'Try real Rijkswaterstaat raster-derived bed heights with an assumed design elevation.', demoLoading: 'Loading survey details…',
    source: 'Survey source', measuredData: 'Measured data', publisher: 'Publisher', license: 'License', sourceLink: 'View original source', demoLoaded: 'Real survey selected. Review the reference, then run the analysis.', demoName: 'RWS Amsterdam–Rhine Canal · measured bed',
    stepData: 'Measured waterbed', surveyUpload: 'Drop your survey here', browse: 'or choose a file', supported: 'CSV with x, y, z columns or GeoTIFF. Coordinates and elevations in metres. Maximum 100 MB per survey file.',
    selectedFile: 'Selected file', remove: 'Remove', chooseFile: 'Choose file', crs: 'Coordinate system', crsHint: 'A projected CRS in metres, e.g. EPSG:28992 (RD New).', datum: 'Vertical datum', datumPlaceholder: 'e.g. NAP', datumHint: 'Use the documented height reference of your data.',
    zConvention: 'Z values represent', elevation: 'Elevation (positive upward)', depth: 'Depth below datum (positive downward)', zHint: 'Depth must be relative to the declared fixed datum, not depth below the water surface.',
    stepReference: 'Reference profile', refType: 'What does the reference represent?', design: 'Design / required bed level', previous: 'An earlier measured survey', underside: 'Verified underside of sediment',
    designHint: 'Calculates material above the design level: potential dredging volume.', previousHint: 'Calculates bed change between dates: deposition and erosion.', undersideHint: 'Estimates layer volume only if the lower boundary is independently verified.',
    refMode: 'Reference surface', constant: 'Flat elevation', file: 'Upload a surface', referenceRequiresFile: 'An earlier survey or sediment underside requires an actual reference surface file.', refElevation: 'Reference elevation', refElevationHint: 'Metres relative to the vertical datum; always positive upward. Example: −5 means 5 m below datum.', demoNote: 'Assumed flat design elevation of {elevation} m {datum}; not an official maintenance profile or a measured sediment boundary.',
    refUpload: 'Drop your reference here', refSupported: 'XYZ CSV or GeoTIFF, with enough coverage of the measured bed.', refMetadata: 'Reference coordinates and heights', sameMetadata: 'Match the survey metadata, or enter the documented reference values.',
    referenceNote: 'Describe this reference', referenceNotePlaceholder: 'e.g. Assumed design elevation, −5 m NAP; not a measured sediment boundary.', referenceNoteHint: 'Required. This description is included with the exported results.',
    stepSettings: 'Processing settings', cellSize: 'Grid cell size', maxEdge: 'Maximum triangle edge', metre: 'm', gridHint: 'Both surfaces are compared on the same grid. Large gaps and unsupported areas remain empty.',
    filter: 'Local outlier detection', filterOff: 'Off', filterFlag: 'Flag for review', filterExclude: 'Exclude flagged points', filterHint: 'Checks deviations from a locally fitted plane using MAD. A review aid: real bed features can also be flagged.',
    advanced: 'Advanced settings & uncertainty', filterK: 'MAD threshold multiplier', filterFloor: 'Minimum residual threshold', neighbors: 'Neighbouring points', sigmaCurrent: 'Survey vertical uncertainty (1σ)', sigmaReference: 'Reference vertical uncertainty (1σ)', optional: 'Optional', uncertaintyHint: 'Supply both values in metres, or leave both empty. One standard deviation; assumes independent vertical errors, not a full spatial uncertainty model.',
    boundary: 'Optional area boundary', boundaryHint: 'GeoJSON Polygon/MultiPolygon in WGS84 longitude/latitude. Projected coordinates require an explicit top-level crs declaration.', boundaryUpload: 'Choose a GeoJSON boundary',
    run: 'Run analysis', running: 'Building surfaces & calculating…', runHint: 'Calculation runs locally. Uploaded files stay on this computer.',
    echoTitle: 'Starting from Sonoptix ECHO?', echoText: 'This prototype starts with validated XYZ or raster bathymetry. Raw ECHO imaging-sonar recordings need a separate, verified georeferencing and bed-reconstruction workflow.',
    workspace: 'Analysis workspace', ready: 'Ready when you are', resultsReady: 'Analysis complete', loadingStatus: 'Processing survey',
    emptyTitle: 'Your survey, in perspective.', emptyText: 'Load the real Dutch example or upload your measurements. Choose a reference and run the analysis to see the comparison here.', emptyStep1: '1 · Import measured bed', emptyStep2: '2 · Define the reference', emptyStep3: '3 · Calculate & inspect',
    difference: 'Difference map', bed: 'Bed surface · 3D', map: 'Survey points', chartHelp: 'Drag to explore · Scroll to zoom · Double-click to reset', trueProportions: 'True proportions · 1× vertical scale',
    verticalScale: 'Vertical scale', verticalAuto: 'Auto · reveal bed relief', verticalTrue: '1× · true proportions', resetBedView: 'Reset 3D view', verticalSummary: '{factor}× vertical exaggeration', verticalScaleNote: 'Vertical scale: {factor}×. Display only; elevations and volumes are unchanged.',
    above: 'Volume above reference', below: 'Volume below reference', validArea: 'Compared area', coverage: 'Area coverage', positiveDescription: 'Positive differences only', negativeDescription: 'Reported separately; never subtracted from removal volume', areaDescription: 'Common valid area of both surfaces', coverageDescription: 'Supported area as a share of the requested area or boundary',
    designResult: 'Potential dredging volume above the chosen design. This does not identify sludge thickness or sediment type.', previousResult: 'Positive differences show bed elevation gain; negative differences show bed elevation loss. This is survey-to-survey change.', undersideResult: 'Layer volume relative to the stated lower boundary. Its interpretation depends on independent verification of that boundary.',
    interpretation: 'What this result means', referenceLabel: 'Reference', quality: 'Survey & calculation', qualityHint: 'Check these indicators before using the volume for a decision.', inputPoints: 'Input points', acceptedPoints: 'Points used', flaggedPoints: 'Flagged points', duplicatePoints: 'Duplicate XY locations', gridCells: 'Grid cells', validCells: 'Compared cells', minDifference: 'Minimum difference', maxDifference: 'Maximum difference', meanDifference: 'Mean difference', gridResolution: 'Grid resolution', coordinateRef: 'Coordinates', heightRef: 'Height reference', netVolume: 'Signed net change', lod95: '95% detection threshold', detectableAbove: 'Above threshold · positive volume', detectableBelow: 'Above threshold · negative volume', noLod: 'Not supplied',
    warnings: 'Review notes', exports: 'Take the result with you', exportsHint: 'Exports include the calculation settings and reference description.', bundle: 'Download full result', cells: 'Grid CSV', geotiff: 'Difference GeoTIFF', summary: 'Summary JSON', points: 'Reviewed points CSV',
    provenance: 'Data & method', method: 'Local outlier screening → Delaunay TIN → common grid → separate positive/negative volumes.', realData: 'Real public bathymetry · raster cell means', userData: 'Uploaded measurements', assumedReference: 'Reference is a user-defined assumption.',
    xAxis: 'Easting', yAxis: 'Northing', xAxisShort: 'X (m)', yAxisShort: 'Y (m)', zAxis: 'Elevation', differenceAxis: 'Bed − reference', bedTrace: 'Measured bed surface', refTrace: 'Reference surface', pointTrace: 'Accepted measurements', flaggedTrace: 'Flagged measurements', emptyCell: 'No supported comparison',
    errorTitle: 'Check your inputs', errorGeneric: 'The analysis could not be completed. Check the input data and settings, then try again.', checkFields: 'Review', networkError: 'The local server could not be reached. Check that the application is running.', surveyRequired: 'Choose a survey file or load the real-data example first.', referenceRequired: 'Choose a reference surface file.', noteRequired: 'Describe the reference so the result can be interpreted correctly.', invalidNumber: 'Check the numeric settings. Grid size, triangle limit and filter thresholds must be positive.', invalidOptional: 'Supply both uncertainty values as non-negative numbers, or leave both empty.', invalidType: 'Choose CSV, TXT, XYZ or GeoTIFF for a surface; GeoJSON or JSON for a boundary.',
    stale: 'Inputs changed. Run the analysis again to refresh the result.',
    errors: {
      hosted_access: "Access denied. Use your project access key.",
      hosted_busy: "The server is processing another survey. Try again shortly.",
      hosted_size: "The survey request exceeds the server limit or has no declared size.",

      invalid_config: 'One or more processing settings are invalid. Check the configuration.', invalid_csv: 'The CSV could not be read. Use a header row with x, y and z columns and consistent separators.', missing_columns: 'The point file is missing required coordinate columns. Use x, y and z headers.', invalid_values: 'The file contains invalid or non-numeric coordinates. Check the data rows.', too_many_points: 'This dataset exceeds the prototype point limit. Use a smaller area or a documented downsampling step.', too_few_points: 'There are too few usable points to build a surface.', invalid_crs: 'The coordinate system could not be read. Use a valid projected EPSG code.', geographic_crs: 'Latitude/longitude degrees cannot be used for this volume calculation. Reproject the data to a suitable CRS in metres.', units_not_meters: 'This prototype requires coordinates and heights in metres.', missing_vertical_datum: 'Provide the documented vertical datum for each surface.', datum_mismatch: 'The surfaces have different vertical datums. Transform them to the same datum before comparing.', crs_mismatch: 'The declared coordinate systems do not match the data or each other. Reproject and correct the declarations.', invalid_reference: 'The reference is missing, invalid or incompatible with the survey.', insufficient_coverage: 'The two surfaces have insufficient common supported coverage. Check their locations, boundary and triangle limit.', degenerate_points: 'The points cannot form a valid surface. They may be collinear or have too few unique XY positions.', unsupported_format: 'This file format is not supported. Use XYZ CSV or GeoTIFF.', invalid_boundary: 'Use a valid GeoJSON Polygon/MultiPolygon. WGS84 longitude/latitude is assumed unless an explicit top-level crs is provided.', file_too_large: 'This file exceeds its {limit} MB upload limit.', processing_failed: 'Surface processing failed. Check the geometry, data coverage and settings.', grid_too_large: 'The requested grid is too large. Increase cell size or choose a smaller area.', raster_metadata: 'The GeoTIFF is missing or has incompatible geospatial metadata. Check its CRS, units and transform.'
    },
    warningMessages: {
      no_uncertainty: 'No survey/reference uncertainty was supplied. Small differences may be measurement noise; no detection threshold is applied.', filter_excluded: 'Flagged outliers were excluded. Review the exported points and check whether real bed features were removed.', filter_flagged: 'Potential outliers are flagged for review and retained in the surface.', duplicates_aggregated: 'Repeated XY positions were aggregated before triangulation.', limited_coverage: 'Some cells have no supported comparison. The volume covers only the common valid area.', design_not_sludge: 'A design comparison measures material above that design, not the physical sludge layer.', previous_not_sludge: 'Comparison with an earlier survey measures bed change, not total sludge thickness.', underside_unverified: 'The software cannot verify that the reference is the sediment underside. Confirm this using independent measurements.', raster_source: 'The survey starts from a published raster. Its original resolution and survey uncertainty constrain the result.', grid_approximation: 'Volume is estimated on a regular grid. Check sensitivity to cell size before making decisions.', edge_limit: 'Triangles longer than the configured limit are masked to avoid bridging unsupported gaps.', support_gap: 'Unsupported gaps are excluded from the calculation; they are not filled with zero difference.'
    }
  },
  nl: {
    hostPublic: "Openbare demo",
    hostDemoHint: "Bekijk twee opgeslagen berekeningen met openbare bodemdata van Rijkswaterstaat en een aangenomen ontwerp op −6,50 m NAP.",
    hostLoad: "Open demoresultaat",
    hostLab: "Verbind met de analyseserver",
    hostPrivacy: "Meetbestanden worden verwerkt op de projectserver. Originele bestanden worden na verwerking verwijderd. Download resultaten voordat ze verlopen, uiterlijk één uur na de berekening. Upload alleen goedgekeurde bestanden.",
    hostKey: "Projecttoegangssleutel",
    hostUnlock: "Verbinden",
    hostLock: "Verbreek verbinding en wis werkruimte",
    hostChecking: "Servertoegang controleren…",
    hostUnlocked: "Verbonden. Je kunt een meting inspecteren of analyseren.",
    hostDemoReady: "Het openbare voorbeeld gebruikt vaste invoer. Maak verbinding om opnieuw te rekenen.",
    hostDemoOnly: "Het openbare voorbeeld gebruikt vaste invoer. Analyseer nieuwe metingen in de lokale applicatie.",
    hostDemoError: "De demo kon niet worden geladen. Vernieuw de pagina en probeer opnieuw.",
    hostOffline: "De analyseserver is niet bereikbaar. Probeer het over een minuut opnieuw of open de openbare demo.",
    hostExpired: "Deze download is verlopen. Voer de analyse opnieuw uit.",
    hostDownloadError: "Het bestand kon niet worden gedownload. Controleer je toegang en probeer opnieuw.",

    pageTitle: 'EASE · Verken sedimentvolumes', brandSub: 'Helder inzicht in waterwegen', language: 'Taal van de interface',
    local: 'Lokaal prototype', eyebrow: 'METING → OPPERVLAK → VOLUME', title: 'Inzicht in wat boven de referentie ligt.',
    intro: 'Vergelijk een gemeten waterbodem met een vastgelegde referentie. Bekijk het oppervlak, controleer de dekking en exporteer een uitlegbare volumeberekening.',
    setup: 'Stel je analyse in', setupSub: 'Gegevens met coördinaten erin. Een transparante vergelijking eruit.',
    demo: 'Laad Nederlandse bodemgegevens', demoHint: 'Probeer echte bodemhoogtes uit een Rijkswaterstaat-raster met een aangenomen ontwerphoogte.', demoLoading: 'Meetgegevens laden…',
    source: 'Bron van de meting', measuredData: 'Meetgegevens', publisher: 'Uitgever', license: 'Licentie', sourceLink: 'Bekijk de oorspronkelijke bron', demoLoaded: 'Echte meting geselecteerd. Controleer de referentie en voer de analyse uit.', demoName: 'RWS Amsterdam-Rijnkanaal · gemeten bodem',
    stepData: 'Gemeten waterbodem', surveyUpload: 'Sleep je meting hierheen', browse: 'of kies een bestand', supported: 'CSV met kolommen x, y, z of GeoTIFF. Coördinaten en hoogtes in meters. Maximaal 100 MB per meetbestand.',
    selectedFile: 'Geselecteerd bestand', remove: 'Verwijderen', chooseFile: 'Kies bestand', crs: 'Coördinatenstelsel', crsHint: 'Een geprojecteerd stelsel in meters, bijv. EPSG:28992 (RD New).', datum: 'Verticaal referentievlak', datumPlaceholder: 'bijv. NAP', datumHint: 'Gebruik de gedocumenteerde hoogtereferentie van je gegevens.',
    zConvention: 'Z-waarden betekenen', elevation: 'Hoogte (positief omhoog)', depth: 'Diepte onder referentievlak (positief omlaag)', zHint: 'Diepte moet ten opzichte van het opgegeven vaste referentievlak zijn, niet onder het wateroppervlak.',
    stepReference: 'Referentieprofiel', refType: 'Wat stelt de referentie voor?', design: 'Ontwerp / vereiste bodemhoogte', previous: 'Een eerdere bodemmeting', underside: 'Vastgestelde onderkant van sediment',
    designHint: 'Berekent materiaal boven het ontwerp: mogelijk baggervolume.', previousHint: 'Berekent bodemverandering tussen metingen: afzetting en erosie.', undersideHint: 'Schat het laagvolume alleen als de ondergrens onafhankelijk is vastgesteld.',
    refMode: 'Referentieoppervlak', constant: 'Vaste hoogte', file: 'Oppervlak uploaden', referenceRequiresFile: 'Een eerdere meting of sedimentonderkant vereist een echt referentiebestand.', refElevation: 'Referentiehoogte', refElevationHint: 'Meters ten opzichte van het referentievlak; altijd positief omhoog. Voorbeeld: −5 is 5 m onder het referentievlak.', demoNote: 'Aangenomen vlakke ontwerphoogte van {elevation} m {datum}; geen officieel onderhoudsprofiel of gemeten sedimentgrens.',
    refUpload: 'Sleep je referentie hierheen', refSupported: 'XYZ CSV of GeoTIFF met voldoende dekking van de gemeten bodem.', refMetadata: 'Coördinaten en hoogtes van de referentie', sameMetadata: 'Gebruik dezelfde metadata als de meting, of vul de gedocumenteerde referentiewaarden in.',
    referenceNote: 'Beschrijf deze referentie', referenceNotePlaceholder: 'Bijv. Aangenomen ontwerphoogte, −5 m NAP; geen gemeten sedimentgrens.', referenceNoteHint: 'Verplicht. Deze beschrijving wordt met de resultaten geëxporteerd.',
    stepSettings: 'Verwerkingsinstellingen', cellSize: 'Rastercelgrootte', maxEdge: 'Maximale driehoekszijde', metre: 'm', gridHint: 'Beide oppervlakken worden op hetzelfde raster vergeleken. Grote gaten en gebieden zonder meetdekking blijven leeg.',
    filter: 'Lokale uitschieterdetectie', filterOff: 'Uit', filterFlag: 'Markeren voor controle', filterExclude: 'Gemarkeerde punten uitsluiten', filterHint: 'Controleert afwijkingen van een lokaal geschat vlak met MAD. Een hulpmiddel: echte bodemvormen kunnen ook worden gemarkeerd.',
    advanced: 'Extra instellingen & onzekerheid', filterK: 'Vermenigvuldigingsfactor MAD', filterFloor: 'Minimale afwijkingsdrempel', neighbors: 'Naburige punten', sigmaCurrent: 'Verticale meetonzekerheid (1σ)', sigmaReference: 'Referentieonzekerheid (1σ)', optional: 'Optioneel', uncertaintyHint: 'Vul beide waarden in meters in, of laat beide leeg. Eén standaardafwijking; neemt onafhankelijke verticale fouten aan, geen volledig ruimtelijk onzekerheidsmodel.',
    boundary: 'Optionele gebiedsgrens', boundaryHint: 'GeoJSON Polygon/MultiPolygon in WGS84 lengte-/breedtegraden. Geprojecteerde coördinaten vereisen een expliciete crs-opgave op hoofdniveau.', boundaryUpload: 'Kies een GeoJSON-gebiedsgrens',
    run: 'Bereken volume', running: 'Oppervlakken maken & berekenen…', runHint: 'De berekening draait lokaal. Bestanden blijven op deze computer.',
    echoTitle: 'Begin je met Sonoptix ECHO?', echoText: 'Dit prototype begint met gevalideerde XYZ- of rasterbodemgegevens. Ruwe ECHO-beelden vragen een aparte, gecontroleerde werkwijze voor plaatsbepaling en bodemreconstructie.',
    workspace: 'Analysewerkruimte', ready: 'Klaar om te beginnen', resultsReady: 'Analyse voltooid', loadingStatus: 'Meting verwerken',
    emptyTitle: 'Je meting, in perspectief.', emptyText: 'Laad het echte Nederlandse voorbeeld of upload je metingen. Kies een referentie en voer de analyse uit om de vergelijking hier te bekijken.', emptyStep1: '1 · Importeer de waterbodem', emptyStep2: '2 · Definieer de referentie', emptyStep3: '3 · Bereken & controleer',
    difference: 'Verschilkaart', bed: 'Waterbodem · 3D', map: 'Meetpunten', chartHelp: 'Sleep om te verkennen · Scroll om te zoomen · Dubbelklik om te herstellen', trueProportions: 'Ware verhoudingen · verticale schaal 1×',
    verticalScale: 'Verticale schaal', verticalAuto: 'Auto · bodemreliëf tonen', verticalTrue: '1× · ware verhoudingen', resetBedView: '3D-weergave herstellen', verticalSummary: '{factor}× verticale vergroting', verticalScaleNote: 'Verticale schaal: {factor}×. Alleen de weergave; hoogtes en volumes blijven gelijk.',
    above: 'Volume boven referentie', below: 'Volume onder referentie', validArea: 'Vergeleken oppervlak', coverage: 'Gebiedsdekking', positiveDescription: 'Alleen positieve verschillen', negativeDescription: 'Apart gerapporteerd; nooit van het te verwijderen volume afgetrokken', areaDescription: 'Gemeenschappelijk geldig oppervlak', coverageDescription: 'Onderbouwd oppervlak als aandeel van het gevraagde gebied of de grens',
    designResult: 'Mogelijk baggervolume boven het gekozen ontwerp. Dit bepaalt geen slibdikte of sedimentsoort.', previousResult: 'Positieve verschillen tonen bodemverhoging; negatieve verschillen tonen bodemverlaging. Dit is verandering tussen metingen.', undersideResult: 'Laagvolume ten opzichte van de opgegeven ondergrens. De betekenis hangt af van onafhankelijke vaststelling van die grens.',
    interpretation: 'Wat dit resultaat betekent', referenceLabel: 'Referentie', quality: 'Meting & berekening', qualityHint: 'Controleer deze indicatoren voordat je het volume gebruikt voor een beslissing.', inputPoints: 'Invoerpunten', acceptedPoints: 'Gebruikte punten', flaggedPoints: 'Gemarkeerde punten', duplicatePoints: 'Dubbele XY-locaties', gridCells: 'Rastercellen', validCells: 'Vergeleken cellen', minDifference: 'Kleinste verschil', maxDifference: 'Grootste verschil', meanDifference: 'Gemiddeld verschil', gridResolution: 'Rasterresolutie', coordinateRef: 'Coördinaten', heightRef: 'Hoogtereferentie', netVolume: 'Netto bodemverandering', lod95: '95%-detectiedrempel', detectableAbove: 'Boven drempel · positief volume', detectableBelow: 'Boven drempel · negatief volume', noLod: 'Niet opgegeven',
    warnings: 'Aandachtspunten', exports: 'Neem het resultaat mee', exportsHint: 'Exports bevatten de rekeninstellingen en referentiebeschrijving.', bundle: 'Download volledig resultaat', cells: 'Raster CSV', geotiff: 'Verschil GeoTIFF', summary: 'Samenvatting JSON', points: 'Gecontroleerde punten CSV',
    provenance: 'Gegevens & methode', method: 'Lokale uitschietercontrole → Delaunay-TIN → gemeenschappelijk raster → aparte positieve/negatieve volumes.', realData: 'Echte openbare bodemgegevens · rastercelgemiddelden', userData: 'Geüploade metingen', assumedReference: 'Referentie is een aanname van de gebruiker.',
    xAxis: 'Oostcoördinaat', yAxis: 'Noordcoördinaat', xAxisShort: 'X (m)', yAxisShort: 'Y (m)', zAxis: 'Hoogte', differenceAxis: 'Bodem − referentie', bedTrace: 'Gemeten bodemoppervlak', refTrace: 'Referentieoppervlak', pointTrace: 'Geaccepteerde meetpunten', flaggedTrace: 'Gemarkeerde meetpunten', emptyCell: 'Geen onderbouwde vergelijking',
    errorTitle: 'Controleer je invoer', errorGeneric: 'De analyse kon niet worden voltooid. Controleer de gegevens en instellingen en probeer opnieuw.', checkFields: 'Controleer', networkError: 'De lokale server is niet bereikbaar. Controleer of de toepassing draait.', surveyRequired: 'Kies een meetbestand of laad eerst het echte voorbeeld.', referenceRequired: 'Kies een bestand voor het referentieoppervlak.', noteRequired: 'Beschrijf de referentie, zodat het resultaat goed kan worden geïnterpreteerd.', invalidNumber: 'Controleer de getallen. Celgrootte, driehoeksgrens en filterdrempels moeten positief zijn.', invalidOptional: 'Vul beide onzekerheden in als niet-negatieve getallen, of laat beide leeg.', invalidType: 'Kies CSV, TXT, XYZ of GeoTIFF voor een oppervlak; GeoJSON of JSON voor een gebiedsgrens.',
    stale: 'Invoer gewijzigd. Voer de analyse opnieuw uit voor een actueel resultaat.',
    errors: {
      hosted_access: "Geen toegang. Gebruik je projecttoegangssleutel.",
      hosted_busy: "De server verwerkt een andere meting. Probeer het zo opnieuw.",
      hosted_size: "Het verzoek is te groot of heeft geen opgegeven bestandsgrootte.",

      invalid_config: 'Een of meer verwerkingsinstellingen zijn ongeldig. Controleer de instellingen.', invalid_csv: 'De CSV kon niet worden gelezen. Gebruik een kopregel met x, y en z en consistente scheidingstekens.', missing_columns: 'Verplichte coördinaatkolommen ontbreken. Gebruik de kolomkoppen x, y en z.', invalid_values: 'Het bestand bevat ongeldige of niet-numerieke coördinaten. Controleer de gegevensregels.', too_many_points: 'Deze dataset overschrijdt de puntlimiet van het prototype. Gebruik een kleiner gebied of gedocumenteerde uitdunning.', too_few_points: 'Er zijn te weinig bruikbare punten om een oppervlak te maken.', invalid_crs: 'Het coördinatenstelsel kon niet worden gelezen. Gebruik een geldige geprojecteerde EPSG-code.', geographic_crs: 'Breedte- en lengtegraden zijn niet geschikt voor deze volumeberekening. Projecteer de gegevens naar een geschikt stelsel in meters.', units_not_meters: 'Dit prototype vereist coördinaten en hoogtes in meters.', missing_vertical_datum: 'Vul het gedocumenteerde verticale referentievlak van elk oppervlak in.', datum_mismatch: 'De oppervlakken gebruiken verschillende verticale referentievlakken. Transformeer ze naar hetzelfde vlak.', crs_mismatch: 'De opgegeven coördinatenstelsels komen niet overeen met de gegevens of met elkaar. Herprojecteer en corrigeer de opgave.', invalid_reference: 'De referentie ontbreekt, is ongeldig of past niet bij de meting.', insufficient_coverage: 'De oppervlakken hebben onvoldoende gemeenschappelijke meetdekking. Controleer locatie, gebiedsgrens en driehoeksgrens.', degenerate_points: 'De punten kunnen geen geldig oppervlak vormen. Ze liggen mogelijk op één lijn of hebben te weinig unieke XY-posities.', unsupported_format: 'Dit bestandsformaat wordt niet ondersteund. Gebruik XYZ CSV of GeoTIFF.', invalid_boundary: 'Gebruik een geldige GeoJSON Polygon/MultiPolygon. WGS84 lengte-/breedtegraden worden aangenomen, tenzij crs expliciet op hoofdniveau staat.', file_too_large: 'Dit bestand overschrijdt de uploadlimiet van {limit} MB.', processing_failed: 'Oppervlakverwerking mislukt. Controleer geometrie, dekking en instellingen.', grid_too_large: 'Het gevraagde raster is te groot. Vergroot de celgrootte of kies een kleiner gebied.', raster_metadata: 'De GeoTIFF mist geometadata of bevat onverenigbare metadata. Controleer stelsel, eenheden en rastertransformatie.'
    },
    warningMessages: {
      no_uncertainty: 'Er is geen meet- of referentieonzekerheid opgegeven. Kleine verschillen kunnen meetruis zijn; er wordt geen detectiedrempel toegepast.', filter_excluded: 'Gemarkeerde uitschieters zijn uitgesloten. Controleer de geëxporteerde punten op verwijderde echte bodemvormen.', filter_flagged: 'Mogelijke uitschieters zijn gemarkeerd en blijven in het oppervlak aanwezig.', duplicates_aggregated: 'Herhaalde XY-posities zijn samengevoegd vóór de triangulatie.', limited_coverage: 'Sommige cellen hebben geen onderbouwde vergelijking. Het volume betreft alleen het gemeenschappelijk geldige gebied.', design_not_sludge: 'Vergelijking met een ontwerp meet materiaal boven dat ontwerp, niet de fysieke sliblaag.', previous_not_sludge: 'Vergelijking met een eerdere meting bepaalt bodemverandering, niet de totale slibdikte.', underside_unverified: 'De software kan niet vaststellen of de referentie de onderkant van sediment is. Bevestig dit met onafhankelijke metingen.', raster_source: 'De meting is afgeleid van een gepubliceerd raster. Oorspronkelijke resolutie en meetonzekerheid begrenzen het resultaat.', grid_approximation: 'Het volume wordt op een regelmatig raster geschat. Controleer de gevoeligheid voor celgrootte vóór gebruik.', edge_limit: 'Driehoeken langer dan de ingestelde grens worden gemaskeerd om niet-gemeten gaten te vermijden.', support_gap: 'Gaten zonder meetdekking zijn uitgesloten; ze worden niet met nulverschil gevuld.'
    }
  }
};

// Survey inspection is independent of the reference and never reports a volume.
Object.assign(window.EASE_I18N.en, {
  supported: 'XYZ CSV, GeoTIFF or a ZIP containing one 3D point shapefile (.shp, .shx, .dbf, .prj). Maximum 100 MB per survey file.',
  refSupported: 'XYZ CSV, GeoTIFF or PointZ shapefile ZIP with matching coordinates and heights.',
  invalidType: 'Choose XYZ CSV, GeoTIFF or PointZ shapefile ZIP for a surface, or GeoJSON for a boundary.',
  inspectSurvey: 'Inspect survey without a reference', inspectRunning: 'Reading survey points…',
  inspectHint: 'Check coordinates, heights and coverage before calculating. No reference or assumed volume is needed.',
  inspectFileRequired: 'Upload a survey file to inspect. The public example has its own documented defaults.',
  previewTitle: 'Survey inspection', previewIntro: 'Inspect the recorded points and check their heights before building a bed surface.',
  previewZRange: 'Elevation range', previewDisplayed: 'Displayed sample points', rangeTo: 'to',
  previewViews: 'Survey inspection views', preview3d: '3D points', previewPlan: 'Plan view',
  previewAboveZero: 'Above datum zero', previewAtOrBelowZero: 'At or below datum zero',
  previewMixedHeights: 'If you expected the bed below datum zero, check the height corrections. Depth and elevation use different reference levels.',
  previewOrbitHint: 'Drag to rotate. Switch to Plan view to select a reach.',
  bedPatches: 'Showing the covered parts of {count} calculation cells as surface patches. Each patch uses the height calculated for that cell.',
  bedFocusPatch: 'Zoom to patch', bedFullReach: 'Show full reach',
  bedFocused: 'Zoomed to a covered patch. Each cell is shown at its calculated height.',
  bedSparse: 'Surface patches could not be drawn. Showing {count} accepted calculation locations.',
  bedSamples: 'Bed samples', refSamples: 'Reference samples',
  previewZoomHint: 'Drag a rectangle to zoom into a short reach. Then choose that visible area for analysis. Double-click to reset the map.',
  useVisibleArea: 'Use visible map area', clearArea: 'Clear area selection', manualArea: 'Enter analysis bounds manually', applyArea: 'Apply bounds',
  selectedArea: 'Analysis bounds (X min, Y min, X max, Y max)', fullExtent: 'No area selected. Analysis will use the full extent.',
  previewGridNote: 'Bounding grid: about {cells} cells at {size} m. Limit: {limit}. Select a smaller reach rather than bridging gaps or using a very coarse grid.',
  previewDatumNote: 'The height datum is your declaration. A shapefile projection describes horizontal coordinates, not whether heights are NAP. Confirm the acquisition and processing record.',
  invalidArea: 'Enter four finite bounds with X min < X max and Y min < Y max.', selectedPoints: 'Points in selected area'
});
Object.assign(window.EASE_I18N.nl, {
  supported: 'XYZ CSV, GeoTIFF of een ZIP met één 3D-puntshapefile (.shp, .shx, .dbf, .prj). Maximaal 100 MB per meetbestand.',
  refSupported: 'XYZ CSV, GeoTIFF of PointZ-shapefile-ZIP met passende coördinaten en hoogtes.',
  invalidType: 'Kies XYZ CSV, GeoTIFF of een PointZ-shapefile-ZIP voor een oppervlak, of GeoJSON voor een gebiedsgrens.',
  inspectSurvey: 'Bekijk meting zonder referentie', inspectRunning: 'Meetpunten lezen…',
  inspectHint: 'Controleer coördinaten, hoogtes en dekking vóór de berekening. Een referentie of aangenomen volume is niet nodig.',
  inspectFileRequired: 'Upload een meetbestand om te bekijken. Het openbare voorbeeld heeft eigen gedocumenteerde instellingen.',
  previewTitle: 'Meting bekijken', previewIntro: 'Bekijk de meetpunten en controleer hun hoogtes voordat je een bodemoppervlak maakt.',
  previewZRange: 'Hoogtebereik', previewDisplayed: 'Getoonde steekproefpunten', rangeTo: 'tot',
  previewViews: 'Weergaven van meetpunten', preview3d: '3D-punten', previewPlan: 'Bovenaanzicht',
  previewAboveZero: 'Boven het referentienulpunt', previewAtOrBelowZero: 'Op of onder het referentienulpunt',
  previewMixedHeights: 'Verwacht je dat de bodem onder het referentienulpunt ligt? Controleer de hoogtecorrecties. Diepte en hoogte hebben verschillende referentieniveaus.',
  previewOrbitHint: 'Sleep om te draaien. Kies het bovenaanzicht om een traject te selecteren.',
  bedPatches: 'De gedekte delen van {count} rekencellen zijn als oppervlakken getekend. Elk vlak toont de berekende hoogte van die cel.',
  bedFocusPatch: 'Inzoomen op vlak', bedFullReach: 'Hele traject tonen',
  bedFocused: 'Ingezoomd op een gedekt gebied. Elke cel toont de berekende hoogte.',
  bedSparse: 'De oppervlakken konden niet worden getekend. Je ziet {count} geldige rekenlocaties.',
  bedSamples: 'Bodemwaarden', refSamples: 'Referentiewaarden',
  previewZoomHint: 'Sleep een rechthoek om op een kort traject in te zoomen. Kies daarna het zichtbare gebied voor analyse. Dubbelklik om de kaart te herstellen.',
  useVisibleArea: 'Gebruik zichtbaar kaartgebied', clearArea: 'Gebiedsselectie wissen', manualArea: 'Analysegrenzen handmatig invoeren', applyArea: 'Grenzen toepassen',
  selectedArea: 'Analysegrenzen (X min, Y min, X max, Y max)', fullExtent: 'Geen gebied geselecteerd. De analyse gebruikt het volledige bereik.',
  previewGridNote: 'Omvattend raster: ongeveer {cells} cellen bij {size} m. Limiet: {limit}. Kies een kleiner traject in plaats van gaten te overbruggen of een erg grof raster te gebruiken.',
  previewDatumNote: 'Het hoogtereferentievlak is jouw opgave. Een shapefile-projectie beschrijft horizontale coördinaten en bevestigt geen NAP-hoogtes. Controleer het meet- en verwerkingsverslag.',
  invalidArea: 'Voer vier eindige grenzen in met X min < X max en Y min < Y max.', selectedPoints: 'Punten in geselecteerd gebied'
});
Object.assign(window.EASE_I18N.en.errors, {
  unsupported_format: 'Use XYZ CSV, GeoTIFF or a ZIP containing one PointZ shapefile.',
  invalid_shapefile: 'Use a readable ZIP with exactly one shapefile and its matching SHX, DBF and PRJ files. The package must fit the prototype limits.',
  shapefile_requires_pointz: 'This importer requires 3D PointZ geometry with a height at every point. A 2D drawing, contour or colour class is not XYZ bathymetry.'
});
Object.assign(window.EASE_I18N.nl.errors, {
  unsupported_format: 'Gebruik XYZ CSV, GeoTIFF of een ZIP met één PointZ-shapefile.',
  invalid_shapefile: 'Gebruik een leesbare ZIP met precies één shapefile en bijbehorende SHX-, DBF- en PRJ-bestanden binnen de limieten van het prototype.',
  shapefile_requires_pointz: 'Deze import vereist 3D-PointZ-geometrie met een hoogte voor elk punt. Een 2D-tekening, contour of kleurklasse is geen XYZ-bodemmeting.'
});
window.EASE_I18N.en.warningMessages.shapefile_source = 'This is processed PointZ geometry. The importer preserves its Z values and does not verify sonar corrections, material type or the declared height datum.';
window.EASE_I18N.nl.warningMessages.shapefile_source = 'Dit is verwerkte PointZ-geometrie. De import behoudt de Z-waarden en controleert geen sonarcorrecties, materiaalsoort of het opgegeven hoogtereferentievlak.';

Object.assign(window.EASE_I18N.en, {
  surfaceMethod:'Surface generation',tinMethod:'Linear TIN',krigingMethod:'Ordinary Kriging (experimental)',
  surfaceHint:'Applies to the measured bed and any uploaded reference. A constant reference is unchanged. Both methods retain the same observed coverage geometry.',
  variogramModel:'Variogram model',spherical:'Spherical',exponential:'Exponential',gaussian:'Gaussian',fitMode:'Variogram parameters',fitAuto:'Fit automatically',fitManual:'Set manually',
  fitHint:'Automatic fitting uses at most 512 observations with a fixed seed. Review the resolved parameters after running. Manual defaults are examples, not survey calibration.',
  nugget:'Nugget (m²)',partialSill:'Partial sill (m²)',krigingRange:'Range (m)',
  nuggetHint:'Unresolved small-scale variation. Observed heights remain exact. This is not a calibrated sonar-noise filter.',
  sillHint:'Spatially correlated variability. Total sill = partial sill + nugget.',
  rangeHint:'Correlation distance. Spherical reaches the sill here. Exponential and Gaussian use PyKrige practical-range conventions.',
  krigingAdvanced:'Advanced Kriging settings',krigingNeighbors:'Maximum neighbours (3 to 64)',krigingRadius:'Maximum search distance (m)',
  radiusHint:'At least three neighbours in the same connected survey coverage are required. Larger distances do not expand the coverage mask.',
  maxSE:'Maximum prediction standard error (m)',seHint:'Optional. Excludes cells above this value for either interpolated surface. Their volume remains unknown.',
  krigingLimits:'Isotropic local model. Maximum 20,000 supported predictions per surface. Use a short reach. Failed fits never switch to TIN automatically.',
  uncertainty:'Kriging uncertainty',uncertaintyRole:'Prediction surface',standardError:'Prediction standard error',
  uncertaintyMapHint:'Model-based point uncertainty in metres. Includes predictions excluded by the uncertainty threshold. It is separate from survey sigma and is not a volume confidence interval.',
  resolvedParameters:'Resolved parameters',predictionExcluded:'Excluded by prediction rules',
  maxEdge:'Coverage triangle limit',gridHint:'Cell size controls integration resolution. The coverage triangle limit masks gaps for both methods. A finer grid adds no measurements.',
  method:'Accepted XYZ points supply either linear TIN or experimental local Ordinary Kriging elevations. Both use bounded observed coverage and the same area-based grid integration. Predictions are not new measurements.'
});
Object.assign(window.EASE_I18N.nl, {
  surfaceMethod:'Oppervlak genereren',tinMethod:'Lineair TIN',krigingMethod:'Ordinary Kriging (experimenteel)',
  surfaceHint:'Geldt voor de gemeten bodem en een geüploade referentie. Een constante referentie blijft gelijk. Beide methoden behouden dezelfde gemeten dekkingsgeometrie.',
  variogramModel:'Variogrammodel',spherical:'Sferisch',exponential:'Exponentieel',gaussian:'Gaussisch',fitMode:'Variogramparameters',fitAuto:'Automatisch aanpassen',fitManual:'Handmatig instellen',
  fitHint:'De automatische aanpassing gebruikt maximaal 512 waarnemingen met een vaste seed. Bekijk na de berekening de gebruikte parameters. Handmatige standaardwaarden zijn voorbeelden, geen meetkalibratie.',
  nugget:'Nugget (m²)',partialSill:'Partiële sill (m²)',krigingRange:'Bereik (m)',
  nuggetHint:'Onopgeloste kleinschalige variatie. Gemeten hoogten blijven exact. Dit is geen gekalibreerd filter voor sonarruis.',
  sillHint:'Ruimtelijk gecorreleerde variatie. Totale sill = partiële sill + nugget.',
  rangeHint:'Correlatieafstand. Het sferische model bereikt hier de sill. Exponentieel en Gaussisch gebruiken de praktische-bereikconventies van PyKrige.',
  krigingAdvanced:'Geavanceerde Kriging-instellingen',krigingNeighbors:'Maximaal aantal buren (3 tot 64)',krigingRadius:'Maximale zoekafstand (m)',
  radiusHint:'Minstens drie buren binnen dezelfde verbonden meetdekking zijn vereist. Een grotere afstand vergroot het dekkingsmasker niet.',
  maxSE:'Maximale voorspellingsstandaardfout (m)',seHint:'Optioneel. Sluit cellen boven deze waarde uit voor elk geïnterpoleerd oppervlak. Hun volume blijft onbekend.',
  krigingLimits:'Isotroop lokaal model. Maximaal 20.000 ondersteunde voorspellingen per oppervlak. Gebruik een kort traject. Een mislukte aanpassing schakelt nooit automatisch over op TIN.',
  uncertainty:'Kriging-onzekerheid',uncertaintyRole:'Voorspellingsoppervlak',standardError:'Voorspellingsstandaardfout',
  uncertaintyMapHint:'Modelonzekerheid op punten in meters. Bevat voorspellingen die door de onzekerheidsgrens zijn uitgesloten. Staat los van meetsigma en is geen betrouwbaarheidsinterval voor volume.',
  resolvedParameters:'Gebruikte parameters',predictionExcluded:'Uitgesloten door voorspellingsregels',
  maxEdge:'Dekkingsdriehoeklimiet',gridHint:'Celgrootte bepaalt de integratieresolutie. De driehoeklimiet maskeert gaten bij beide methoden. Een fijner raster voegt geen metingen toe.',
  method:'Geaccepteerde XYZ-punten leveren hoogten via lineair TIN of experimentele lokale Ordinary Kriging. Beide gebruiken begrensde meetdekking en dezelfde oppervlaktegewogen rasterintegratie. Voorspellingen zijn geen nieuwe metingen.'
});
for (const lang of ['en','nl']) {
  Object.assign(window.EASE_I18N[lang].errors, lang === 'en' ? {
    kriging_fit_failed:'The variogram could not be fitted reliably. Inspect the data or set defensible manual parameters. No TIN fallback was used.',
    kriging_solve_failed:'A local Kriging system failed numerically. Review the model and neighbourhood settings. No TIN fallback was used.',
    kriging_limit:'Kriging supports at most 20,000 calculation locations per surface. Select a shorter reach or a coarser grid.',
    kriging_no_predictions:'No calculation cells passed the Kriging support, neighbour and uncertainty rules. Inspect the settings. Excluded volume is unknown.'
  } : {
    kriging_fit_failed:'Het variogram kon niet betrouwbaar worden aangepast. Controleer de data of stel onderbouwde parameters handmatig in. TIN is niet als terugval gebruikt.',
    kriging_solve_failed:'Een lokaal Kriging-stelsel faalde numeriek. Controleer model en buurtinstellingen. TIN is niet als terugval gebruikt.',
    kriging_limit:'Kriging ondersteunt maximaal 20.000 rekenlocaties per oppervlak. Kies een korter traject of grover raster.',
    kriging_no_predictions:'Geen rekencellen voldeden aan de Kriging-regels voor dekking, buren en onzekerheid. Controleer de instellingen. Uitgesloten volume is onbekend.'
  });
  window.EASE_I18N[lang].warningMessages.kriging_experimental = lang === 'en'
    ? 'Experimental Ordinary Kriging. Review the fitted variogram and validate withheld measurements. Prediction uncertainty excludes model misspecification and systematic survey errors. Excluded volume is unknown.'
    : 'Experimentele Ordinary Kriging. Controleer het aangepaste variogram en valideer met achtergehouden metingen. Voorspellingsonzekerheid omvat geen onjuist model of systematische meetfouten. Uitgesloten volume is onbekend.';
}

Object.assign(window.EASE_I18N.en, {excluded_insufficient_neighbors:'Excluded: too few bed neighbours',excluded_reference_insufficient_neighbors:'Excluded: too few reference neighbours',excluded_uncertainty_threshold:'Excluded: standard-error threshold',excluded_outside_support:'Excluded: unsupported sample'});
Object.assign(window.EASE_I18N.nl, {excluded_insufficient_neighbors:'Uitgesloten: te weinig bodemburen',excluded_reference_insufficient_neighbors:'Uitgesloten: te weinig referentieburen',excluded_uncertainty_threshold:'Uitgesloten: standaardfoutgrens',excluded_outside_support:'Uitgesloten: niet-ondersteund monster'});

Object.assign(window.EASE_I18N.en, {
  profileMode: 'Standard design profile', profileCode: 'Profile code', profileWater: 'Design water level (m NAP)',
  profileHint: 'Use a standard Zuiderzeeland profile for one straight reach with a constant design level. Upload RD New points with elevations in m NAP.',
  profileLevelConfirmed: 'The design water level is confirmed for this reach.', profileAssumed: 'Assumed',
  profileCoverage: 'Survey coverage', profileTrack: 'Single survey track', profileArea: 'Survey across the canal',
  profileTrackHint: 'Compare elevations along the track. Volumes require measurements across the canal.',
  profileAreaHint: 'Calculate volume over the supported overlap with the design.',
  profileAlignment: 'Reach alignment', profileFitted: 'Fit a straight line to centreline soundings', profileEndpoints: 'Enter design endpoints',
  profileEndpointsHint: 'Enter the two ends of the straight design centreline in RD New metres.',
  profileNAPConfirmed: 'I confirmed that survey Z values are corrected elevations in m NAP.',
  profileSounding: 'Matching Hydromagic SND file',
  profileSoundingHint: 'Pair the original survey export with its SND file to exclude soundings with missing height corrections.',
  surveyPreprocess: 'Preprocess survey with Hydromagic SND',
  preprocessInspect: 'Preprocess and inspect survey',
  preprocessSoundingRequired: 'Choose the Hydromagic SND file that matches the survey export.',
  preprocessRetained: 'Retained soundings', preprocessExcluded: 'Soundings excluded for missing corrections',
  preprocessPreviewHint: 'The preview shows the retained soundings. Confirm their elevations in m NAP before calculating volume.',
  profileNoteHint: 'Optional. Record where the design level and alignment came from.',
  profileRun: 'Compare with design', profileResult: 'Design profile comparison', profile3D: '3D overlay', profileAlong: 'Along the reach',
  profileProvisional: 'Provisional comparison. Review the source of the water level, alignment and survey heights in the export.',
  profileBed: 'Flat design bed', profileReachLength: 'Reach length', profileCompared: 'Compared soundings',
  profileWithheld: 'Missing height correction', profileOutside: 'Soundings outside design',
  profileFitResult: 'Alignment fitted to the centreline survey.', profileEndpointsResult: 'Alignment from the supplied endpoints.',
  profileDistance: 'Distance along reach (m)', profileAlongAxis: 'Along reach (m)', profileOffset: 'Offset (m)', profileHeight: 'Elevation (m NAP)',
  profilePointDesign: 'Design at sounding', profileObservations: 'Survey soundings',
  profileScale: 'Display scale relative to the reach: {across}× across and {up}× vertically.',
  profileExportDesign: 'Design XYZ', profileExportComparison: 'Point comparison CSV', profileEnterWater: 'Enter a signed design water level in m NAP.',
});
Object.assign(window.EASE_I18N.nl, {
  profileMode: 'Standaard ontwerpprofiel', profileCode: 'Profielcode', profileWater: 'Ontwerpwaterpeil (m NAP)',
  profileHint: 'Gebruik een standaardprofiel van Zuiderzeeland voor één recht traject met een constant ontwerppeil. Upload RD New-punten met hoogtes in m NAP.',
  profileLevelConfirmed: 'Het ontwerpwaterpeil is bevestigd voor dit traject.', profileAssumed: 'Aangenomen',
  profileCoverage: 'Meetdekking', profileTrack: 'Enkele meetlijn', profileArea: 'Meting over de breedte',
  profileTrackHint: 'Vergelijk hoogtes langs de meetlijn. Voor volumes zijn metingen over de breedte nodig.',
  profileAreaHint: 'Bereken het volume binnen het gemeten deel van het ontwerp.',
  profileAlignment: 'Ligging van het traject', profileFitted: 'Pas een rechte lijn aan op metingen langs de hartlijn', profileEndpoints: 'Voer de ontwerpeindpunten in',
  profileEndpointsHint: 'Voer beide eindpunten van de rechte ontwerphartlijn in RD New-meters in.',
  profileNAPConfirmed: 'Ik heb bevestigd dat de Z-waarden gecorrigeerde hoogtes in m NAP zijn.',
  profileSounding: 'Bijbehorend Hydromagic SND-bestand',
  profileSoundingHint: 'Koppel de oorspronkelijke export aan het SND-bestand om peilingen met ontbrekende hoogtecorrecties uit te sluiten.',
  surveyPreprocess: 'Meting voorbewerken met Hydromagic SND',
  preprocessInspect: 'Meting voorbewerken en bekijken',
  preprocessSoundingRequired: 'Kies het Hydromagic SND-bestand dat bij de meetexport hoort.',
  preprocessRetained: 'Behouden peilingen', preprocessExcluded: 'Uitgesloten peilingen door ontbrekende correcties',
  preprocessPreviewHint: 'De weergave toont de behouden peilingen. Bevestig hun hoogtes in m NAP voordat je het volume berekent.',
  profileNoteHint: 'Optioneel. Noteer de bron van het ontwerppeil en de ligging.',
  profileRun: 'Vergelijk met ontwerp', profileResult: 'Vergelijking met het ontwerpprofiel', profile3D: '3D-weergave', profileAlong: 'Langs het traject',
  profileProvisional: 'Voorlopige vergelijking. Controleer de herkomst van het waterpeil, de ligging en de meethoogtes in de export.',
  profileBed: 'Vlakke ontwerpbodem', profileReachLength: 'Trajectlengte', profileCompared: 'Vergeleken peilingen',
  profileWithheld: 'Ontbrekende hoogtecorrectie', profileOutside: 'Peilingen buiten ontwerp',
  profileFitResult: 'Ligging afgeleid van metingen langs de hartlijn.', profileEndpointsResult: 'Ligging op basis van de opgegeven eindpunten.',
  profileDistance: 'Afstand langs het traject (m)', profileAlongAxis: 'Langs traject (m)', profileOffset: 'Afstand tot as (m)', profileHeight: 'Hoogte (m NAP)',
  profilePointDesign: 'Ontwerp bij peiling', profileObservations: 'Peilingen',
  profileScale: 'Weergaveschaal ten opzichte van het traject: {across}× in de breedte en {up}× verticaal.',
  profileExportDesign: 'Ontwerp-XYZ', profileExportComparison: 'Puntvergelijking CSV', profileEnterWater: 'Voer een ontwerpwaterpeil in m NAP in, inclusief het teken.',
});
Object.assign(window.EASE_I18N.en.errors, {
  profile_coordinates: 'Design profiles require RD New (EPSG:28992) and positive-up elevations in m NAP.',
  profile_endpoints: 'Enter both endpoints of the straight design reach.',
  profile_area_requirements: 'An area survey needs design endpoints and corrected survey elevations.',
  profile_heights_required: 'Confirm corrected NAP elevations or provide the matching processed Hydromagic SND file for a track.',
  profile_points_required: 'Upload a processed XYZ file or PointZ ZIP for the design profile.',
  profile_sounding_mismatch: 'The SND file could not be matched to this export. Check the processing revision and point order.',
  profile_alignment: 'Use distinct design endpoints or a long, narrow centreline track with gaps of 25 m or less.',
  profile_overlap: 'No accepted soundings fall within the design reach.',
  profile_export_limit: 'The reach is too long for a 1 m design export. Select a shorter straight reach.',
  preprocess_coordinates: 'SND preprocessing requires a processed XYZ file or PointZ ZIP in RD New with Z as elevations in m NAP.',
  preprocess_no_points: 'All soundings are missing a height correction. Check the survey export and its matching SND file.',
  preprocess_volume_heights: 'Confirm the retained NAP elevations in Measured waterbed before calculating volume.',
});
Object.assign(window.EASE_I18N.nl.errors, {
  profile_coordinates: 'Ontwerpprofielen vereisen RD New (EPSG:28992) en hoogtes in m NAP, positief omhoog.',
  profile_endpoints: 'Voer beide eindpunten van het rechte ontwerptraject in.',
  profile_area_requirements: 'Voor een oppervlaktemeting zijn ontwerpeindpunten en gecorrigeerde hoogtes nodig.',
  profile_heights_required: 'Bevestig gecorrigeerde NAP-hoogtes of voeg bij één meetlijn het bijbehorende verwerkte Hydromagic SND-bestand toe.',
  profile_points_required: 'Upload een verwerkt XYZ-bestand of een PointZ-ZIP voor het ontwerpprofiel.',
  profile_sounding_mismatch: 'Het SND-bestand komt niet overeen met de export. Controleer de verwerkingsversie en puntvolgorde.',
  profile_alignment: 'Gebruik verschillende ontwerpeindpunten of een lange, smalle hartlijnmeting met tussenruimten van maximaal 25 m.',
  profile_overlap: 'Er vallen geen bruikbare peilingen binnen het ontwerptraject.',
  profile_export_limit: 'Dit traject is te lang voor een ontwerpexport op 1 m. Kies een korter recht traject.',
  preprocess_coordinates: 'SND-voorbewerking vereist een verwerkt XYZ-bestand of PointZ-ZIP in RD New met Z als hoogte in m NAP.',
  preprocess_no_points: 'Bij alle peilingen ontbreekt een hoogtecorrectie. Controleer de meetexport en het bijbehorende SND-bestand.',
  preprocess_volume_heights: 'Bevestig de behouden NAP-hoogtes bij Gemeten waterbodem voordat je het volume berekent.',
});
window.EASE_I18N.en.warningMessages.profile_provisional = window.EASE_I18N.en.profileProvisional;
window.EASE_I18N.nl.warningMessages.profile_provisional = window.EASE_I18N.nl.profileProvisional;
window.EASE_I18N.en.warningMessages.survey_heights_screened = 'The calculation used the survey points retained by the SND height check.';
window.EASE_I18N.nl.warningMessages.survey_heights_screened = 'De berekening gebruikt de meetpunten die na de SND-hoogtecontrole zijn behouden.';
