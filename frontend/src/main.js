import { createApp, onMounted, ref } from 'vue'
import './styles.css'

const App = {
  setup() {
    const health = ref({ status: 'loading', api: 'checking', database: 'checking', redis: 'checking' })
    const version = ref({ version: '0.1.0-alpha1', codename: 'Foundation' })

    onMounted(async () => {
      try {
        const [healthResponse, versionResponse] = await Promise.all([
          fetch('/api/v1/health'),
          fetch('/api/v1/version')
        ])
        health.value = await healthResponse.json()
        version.value = await versionResponse.json()
      } catch (error) {
        health.value = {
          status: 'offline',
          api: 'offline',
          database: 'unknown',
          redis: 'unknown'
        }
      }
    })

    return { health, version }
  },
  template: `
    <main class="shell">
      <section class="hero">
        <p class="eyebrow">VaultKeeper</p>
        <h1>Simple. Observable. Recoverable.</h1>
        <p class="subtitle">Linux-first backup orchestration, built for the administrator who gets called at 02:00.</p>
      </section>

      <section class="panel">
        <div class="release">
          <div>
            <span class="label">Release</span>
            <strong>{{ version.version }}</strong>
          </div>
          <div>
            <span class="label">Codename</span>
            <strong>{{ version.codename }}</strong>
          </div>
        </div>

        <div class="status-grid">
          <article v-for="service in ['api', 'database', 'redis']" :key="service" class="status-card">
            <span class="label">{{ service }}</span>
            <strong :class="['state', health[service]]">{{ health[service] }}</strong>
          </article>
        </div>
      </section>
    </main>
  `
}

createApp(App).mount('#app')
