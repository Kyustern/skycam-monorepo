import { mkdir, writeFile } from "node:fs/promises"
import { dirname, join, relative } from "node:path"

type Secrets = {
    GOOGLE_API_KEY?: string
    googleTilesApiKey?: string
    googleApiKey?: string,
    DEFAULT_LOCATION?: {
        latitude: number,
        longitude: number,
        baro_altitude: number
    }
}

type BoundingVolume = {
    region?: number[]
    sphere?: number[]
    box?: number[]
}

type TilesetContent = {
    uri?: string
    url?: string
}

type TilesetTile = {
    boundingVolume?: BoundingVolume
    content?: TilesetContent
    contents?: TilesetContent[]
    children?: TilesetTile[]
}

type TilesetJson = {
    root?: TilesetTile
}

type Options = {
    outDir: string
    maxResources: number
    rootUrl: string
    apiKey: string
    target?: TargetLocation
}

type TargetLocation = {
    latitude: number
    longitude: number
    latitudeRadians: number
    longitudeRadians: number
    radiusMeters: number
    ecef: number[]
}

// const DEFAULT_ROOT_URL = "https://tile.googleapis.com/v1/3dtiles/datasets/CgIYAQ/files/AJVsH2w9m9Y32xKeiNBaUNLoL_OZcHWeEOzqh97duOJ9HR6VjR6Hloc9x5Cfkz_yfbZtSTZhXYeGylLjhHigpBLdZRr5witL51clhElh05-Hatz8plN5XaKx-lK3MYfcyTc0Eq-280ZkS2VqLyq5GfdBmlCfX2kWuA.json"
// const DEFAULT_ROOT_URL = "https://tile.googleapis.com/v1/3dtiles/datasets/CgIYAQ/files/AJVsH2w9m9Y32xKeiNBaUNLoL.json"
const DEFAULT_ROOT_URL = "https://tile.googleapis.com/v1/3dtiles/root.json"
const DEFAULT_OUT_DIR = "public/assets/3d"
const DEFAULT_MAX_RESOURCES = 250
const DEFAULT_RADIUS_KM = 1
const EARTH_RADIUS_METERS = 6378137
// const DEFAULT_MAX_RESOURCES = 20

const readSecrets = async () => {
    const secretsFile = Bun.file("secrets.json")

    if (!(await secretsFile.exists())) {
        throw new Error("Missing secrets.json")
    }

    return await secretsFile.json() as Secrets
}

const readGoogleApiKey = (secrets: Secrets) => {
    const apiKey = secrets.GOOGLE_API_KEY ?? secrets.googleTilesApiKey ?? secrets.googleApiKey

    if (typeof apiKey !== "string" || apiKey.length === 0) {
        throw new Error(
            "Missing Google API key in secrets.json. Add GOOGLE_API_KEY, googleTilesApiKey, or googleApiKey."
        )
    }

    return apiKey
}

const readOption = (name: string) => {
    const prefix = `--${name}=`
    const arg = Bun.argv.find(value => value.startsWith(prefix))

    return arg ? arg.slice(prefix.length) : undefined
}

const readNumberOption = (name: string) => {
    const value = readOption(name)

    return value === undefined ? undefined : Number(value)
}

const readTargetLocation = (secrets: Secrets): TargetLocation | undefined => {
    if (readOption("all") === "true") return undefined

    const latitude = readNumberOption("lat") ?? secrets.DEFAULT_LOCATION?.latitude
    const longitude = readNumberOption("lon") ?? secrets.DEFAULT_LOCATION?.longitude
    const radiusKm = readNumberOption("radius-km") ?? DEFAULT_RADIUS_KM

    if (latitude === undefined && longitude === undefined) return undefined
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        throw new Error("Provide both --lat and --lon as valid numbers")
    }
    if (!Number.isFinite(radiusKm) || radiusKm < 0) {
        throw new Error("--radius-km must be a positive number")
    }

    const latitudeRadians = latitude * Math.PI / 180
    const longitudeRadians = longitude * Math.PI / 180
    const cosLatitude = Math.cos(latitudeRadians)

    return {
        latitude,
        longitude,
        latitudeRadians,
        longitudeRadians,
        radiusMeters: radiusKm * 1000,
        ecef: [
            EARTH_RADIUS_METERS * cosLatitude * Math.cos(longitudeRadians),
            EARTH_RADIUS_METERS * cosLatitude * Math.sin(longitudeRadians),
            EARTH_RADIUS_METERS * Math.sin(latitudeRadians),
        ],
    }
}

const readOptions = (apiKey: string, secrets: Secrets): Options => {
    const outDir = readOption("out") ?? DEFAULT_OUT_DIR
    const maxResources = Number(readOption("max-resources") ?? DEFAULT_MAX_RESOURCES)
    const rootUrl = readOption("root-url") ?? DEFAULT_ROOT_URL
    const url = new URL(rootUrl)

    if (!url.searchParams.has("key")) {
        url.searchParams.set("key", apiKey)
    }

    if (!Number.isFinite(maxResources) || maxResources < 1) {
        throw new Error("--max-resources must be a positive number")
    }

    return {
        outDir,
        maxResources,
        rootUrl: url.toString(),
        apiKey,
        target: readTargetLocation(secrets),
    }
}

const sanitizePathPart = (value: string) => {
    return value.replaceAll(":", "_").replaceAll("*", "_").replaceAll("?", "_")
}

const localPathForUrl = (url: URL, outDir: string, isRoot: boolean) => {
    if (isRoot) return join(outDir, "root.json")

    const pathParts = url.pathname
        .split("/")
        .filter(Boolean)
        .map(sanitizePathPart)

    if (pathParts.length === 0) pathParts.push("index")

    return join(outDir, ...pathParts)
}

const isJsonResponse = (url: URL, response: Response) => {
    const contentType = response.headers.get("content-type") ?? ""

    return contentType.includes("application/json") || url.pathname.endsWith(".json")
}

const contentUri = (content: TilesetContent) => {
    return content.uri ?? content.url
}

const setContentUri = (content: TilesetContent, uri: string) => {
    if (content.uri !== undefined) {
        content.uri = uri
        return
    }

    content.url = uri
}

const toRelativeUri = (fromFile: string, toFile: string) => {
    const path = relative(dirname(fromFile), toFile)

    return path.startsWith(".") ? path : `./${path}`
}

const normalizeRadians = (value: number) => {
    const twoPi = Math.PI * 2
    let normalized = value % twoPi

    if (normalized < -Math.PI) normalized += twoPi
    if (normalized > Math.PI) normalized -= twoPi

    return normalized
}

const isLongitudeInRegion = (longitude: number, west: number, east: number) => {
    const normalizedLongitude = normalizeRadians(longitude)
    const normalizedWest = normalizeRadians(west)
    const normalizedEast = normalizeRadians(east)

    if (normalizedWest <= normalizedEast) {
        return normalizedLongitude >= normalizedWest && normalizedLongitude <= normalizedEast
    }

    return normalizedLongitude >= normalizedWest || normalizedLongitude <= normalizedEast
}

const clamp = (value: number, min: number, max: number) => {
    return Math.min(Math.max(value, min), max)
}

const angularDistanceMeters = (
    latitudeA: number,
    longitudeA: number,
    latitudeB: number,
    longitudeB: number
) => {
    const deltaLatitude = latitudeB - latitudeA
    const deltaLongitude = longitudeB - longitudeA
    const sinDeltaLatitude = Math.sin(deltaLatitude / 2)
    const sinDeltaLongitude = Math.sin(deltaLongitude / 2)
    const haversine = sinDeltaLatitude * sinDeltaLatitude +
        Math.cos(latitudeA) * Math.cos(latitudeB) * sinDeltaLongitude * sinDeltaLongitude

    return EARTH_RADIUS_METERS * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine))
}

const closestLongitudeInRegion = (longitude: number, west: number, east: number) => {
    if (isLongitudeInRegion(longitude, west, east)) return longitude

    const normalizedLongitude = normalizeRadians(longitude)
    const normalizedWest = normalizeRadians(west)
    const normalizedEast = normalizeRadians(east)
    const westDistance = Math.abs(normalizeRadians(normalizedLongitude - normalizedWest))
    const eastDistance = Math.abs(normalizeRadians(normalizedLongitude - normalizedEast))

    return westDistance <= eastDistance ? normalizedWest : normalizedEast
}

const regionIntersectsTargetRadius = (region: number[], target: TargetLocation) => {
    const [west, south, east, north] = region
    const closestLatitude = clamp(target.latitudeRadians, south, north)
    const closestLongitude = closestLongitudeInRegion(target.longitudeRadians, west, east)
    const closestDistanceMeters = angularDistanceMeters(
        target.latitudeRadians,
        target.longitudeRadians,
        closestLatitude,
        closestLongitude
    )

    return closestDistanceMeters <= target.radiusMeters
}

const distance = (a: number[], b: number[]) => {
    return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2])
}

const sphereIntersectsTargetRadius = (sphere: number[], target: TargetLocation) => {
    if (sphere.length < 4) return true

    return distance(target.ecef, sphere.slice(0, 3)) <= sphere[3] + target.radiusMeters
}

const boxIntersectsTargetRadius = (box: number[], target: TargetLocation) => {
    if (box.length < 12) return true

    const center = box.slice(0, 3)
    const halfAxisX = box.slice(3, 6)
    const halfAxisY = box.slice(6, 9)
    const halfAxisZ = box.slice(9, 12)
    const boundingSphereRadius = Math.hypot(
        Math.hypot(...halfAxisX),
        Math.hypot(...halfAxisY),
        Math.hypot(...halfAxisZ)
    )

    return distance(target.ecef, center) <= boundingSphereRadius + target.radiusMeters
}

const tileIntersectsTarget = (tile: TilesetTile, target: TargetLocation | undefined) => {
    if (!target) return true

    const boundingVolume = tile.boundingVolume
    if (!boundingVolume) return true
    if (boundingVolume.region) return regionIntersectsTargetRadius(boundingVolume.region, target)
    if (boundingVolume.sphere) return sphereIntersectsTargetRadius(boundingVolume.sphere, target)
    if (boundingVolume.box) return boxIntersectsTargetRadius(boundingVolume.box, target)

    return true
}

const withApiKey = (url: URL, apiKey: string) => {
    const authenticatedUrl = new URL(url)

    if (authenticatedUrl.hostname === "tile.googleapis.com" && !authenticatedUrl.searchParams.has("key")) {
        authenticatedUrl.searchParams.set("key", apiKey)
    }

    return authenticatedUrl
}

const resolveContentUrl = (uri: string, baseUrl: URL) => {
    const url = new URL(uri, baseUrl)

    if (
        url.hostname === "tile.googleapis.com" &&
        !url.searchParams.has("session") &&
        baseUrl.searchParams.has("session")
    ) {
        url.searchParams.set("session", baseUrl.searchParams.get("session") ?? "")
    }

    return url
}

const redactApiKey = (url: URL) => {
    const redactedUrl = new URL(url)

    if (redactedUrl.searchParams.has("key")) {
        redactedUrl.searchParams.set("key", "REDACTED")
    }

    return redactedUrl.toString()
}

const main = async () => {
    const secrets = await readSecrets()
    const apiKey = readGoogleApiKey(secrets)
    const options = readOptions(apiKey, secrets)
    console.log("options", options);
    const visited = new Set<string>()
    let downloadedResources = 0

    const processResource = async (resourceUrl: URL, isRoot = false): Promise<string> => {
        const cacheKey = resourceUrl.toString()
        const localPath = localPathForUrl(resourceUrl, options.outDir, isRoot)

        if (visited.has(cacheKey)) return localPath
        if (downloadedResources >= options.maxResources) {
            throw new Error(`Reached --max-resources limit (${options.maxResources})`)
        }

        visited.add(cacheKey)
        downloadedResources += 1

        const fetchUrl = withApiKey(resourceUrl, options.apiKey)
        const response = await fetch(fetchUrl).catch(error => {
            throw new Error(`Failed to fetch ${redactApiKey(fetchUrl)}: ${error.message}`)
        })

        if (!response.ok) {
            throw new Error(`Failed to fetch ${redactApiKey(fetchUrl)}: ${response.status} ${response.statusText}`)
        }

        await mkdir(dirname(localPath), { recursive: true })

        if (!isJsonResponse(resourceUrl, response)) {
            await writeFile(localPath, new Uint8Array(await response.arrayBuffer()))
            return localPath
        }

        const processContent = async (content: TilesetContent) => {
            const uri = contentUri(content)
            if (!uri) return

            const childUrl = resolveContentUrl(uri, resourceUrl)
            const childLocalPath = await processResource(childUrl)
            setContentUri(content, toRelativeUri(localPath, childLocalPath))
        }

        const processTile = async (tile: TilesetTile) => {
            if (!tileIntersectsTarget(tile, options.target)) return false

            if (tile.content) await processContent(tile.content)
            if (tile.contents) {
                for (const content of tile.contents) {
                    await processContent(content)
                }
            }

            if (tile.children) {
                const keptChildren: TilesetTile[] = []

                for (const child of tile.children) {
                    if (await processTile(child)) {
                        keptChildren.push(child)
                    }
                }

                tile.children = keptChildren
            }

            return true
        }

        const tileset = await response.json() as TilesetJson
        if (tileset.root) await processTile(tileset.root)

        await writeFile(localPath, `${JSON.stringify(tileset, null, 2)}\n`)
        return localPath
    }

    const rootPath = await processResource(new URL(options.rootUrl), true)
    console.log(`Stored ${downloadedResources} resources in ${options.outDir}`)
    console.log(`Root tileset: ${rootPath}`)

    if (options.target) {
        console.log(
            `Filtered around lat/lon: ${options.target.latitude}, ${options.target.longitude} ` +
            `with radius ${options.target.radiusMeters / 1000}km`
        )
    }
}

main().catch(error => {
    console.error(error)
    process.exit(1)
})
