import { readFileSync } from "node:fs"
import { isAbsolute, join, resolve } from "node:path"

type Secrets = {
    GOOGLE_API_KEY?: string
    googleApiKey?: string
    googleTilesApiKey?: string
}

const PORT = Number(Bun.env.PORT ?? 3000)
const HOSTNAME = "localhost"
const DEFAULT_TEMPLATE_PATH = join(import.meta.dir, "tile-test.html")
const SECRETS_PATH = join(process.cwd(), "secrets.json")
const KEY_PLACEHOLDER_MATCH = "#KEYPLACEHOLDER#"
const GOOGLE_API_KEY_PLACEHOLDER_MATCH = "YOUR_API_KEY"

const readOption = (name: string) => {
    const prefix = `--${name}=`
    const arg = Bun.argv.find(value => value.startsWith(prefix))

    return arg ? arg.slice(prefix.length) : undefined
}

const readTemplatePath = () => {
    const templatePath = readOption("template") ?? Bun.argv[2] ?? DEFAULT_TEMPLATE_PATH

    return isAbsolute(templatePath) ? templatePath : resolve(process.cwd(), templatePath)
}

const readGoogleApiKey = () => {
    const secrets = JSON.parse(readFileSync(SECRETS_PATH, "utf-8")) as Secrets
    const apiKey = secrets.GOOGLE_API_KEY ?? secrets.googleTilesApiKey ?? secrets.googleApiKey

    if (typeof apiKey !== "string" || apiKey.length === 0) {
        throw new Error(
            "Missing Google API key in secrets.json. Add GOOGLE_API_KEY, googleTilesApiKey, or googleApiKey."
        )
    }

    return apiKey
}

const templatePath = readTemplatePath()
const template = readFileSync(templatePath, "utf-8")
const googleApiKey = readGoogleApiKey()
const html = template
    .replaceAll(KEY_PLACEHOLDER_MATCH, googleApiKey)
    .replaceAll(GOOGLE_API_KEY_PLACEHOLDER_MATCH, googleApiKey)

Bun.serve({
    port: PORT,
    hostname: HOSTNAME,
    fetch(request) {
        const url = new URL(request.url)

        if (url.pathname !== "/" && url.pathname !== "/tile-test.html") {
            return new Response("Not found", { status: 404 })
        }

        return new Response(html, {
            headers: {
                "Content-Type": "text/html; charset=utf-8",
            },
        })
    },
})

console.log(`Cesium tile test: http://${HOSTNAME}:${PORT}/`)
console.log(`Serving template: ${templatePath}`)
