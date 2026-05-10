/** Offline action queue backed by IndexedDB for PWA resilience. */

interface OfflineAction {
  id?: number;
  method: string;
  url: string;
  body?: unknown;
  timestamp: number;
}

const DB_NAME = "aigctp-offline";
const STORE_NAME = "actions";
const DB_VERSION = 1;

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("IndexedDB not available"));
      return;
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE_NAME, {
        keyPath: "id",
        autoIncrement: true,
      });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function enqueueOfflineAction(action: Omit<OfflineAction, "id" | "timestamp">): Promise<void> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      tx.objectStore(STORE_NAME).add({ ...action, timestamp: Date.now() });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } catch {
    // IndexedDB not available — queue is unavailable
  }
}

export async function dequeueAllOfflineActions(): Promise<number> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const getAllReq = store.getAll();

      getAllReq.onsuccess = async () => {
        const actions: OfflineAction[] = getAllReq.result;
        let replayed = 0;
        for (const action of actions) {
          try {
            await fetch(action.url, {
              method: action.method,
              headers: { "Content-Type": "application/json" },
              credentials: "include",
              body: action.body ? JSON.stringify(action.body) : undefined,
            });
            if (action.id !== undefined) store.delete(action.id);
            replayed++;
          } catch {
            break; // Network still down — stop replaying, keep remaining in queue
          }
        }
        resolve(replayed);
      };
      getAllReq.onerror = () => reject(getAllReq.error);
    });
  } catch {
    return 0;
  }
}

export async function getOfflineQueueSize(): Promise<number> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const req = tx.objectStore(STORE_NAME).count();
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  } catch {
    return 0;
  }
}
