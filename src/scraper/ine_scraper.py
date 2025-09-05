"""
Scraper para INE.Stat - Módulos de Agua y Aire
"""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from playwright.async_api import async_playwright, Browser, Page, Download

from config.settings import (
    BASE_URL, DATA_DIR, SCRAPER_CONFIG, BROWSER_CONFIG, 
    MODULES_TO_SCRAPE
)
from src.utils.logger import get_logger

logger = get_logger()

class INEScraper:
    """Scraper para el sitio INE.Stat"""
    
    def __init__(self, browser_config: Dict = None, scraper_config: Dict = None):
        """
        Inicializar scraper con configuraciones personalizables
        
        Args:
            browser_config: Configuración personalizada del navegador
            scraper_config: Configuración personalizada del scraper
        """
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.downloads_dir = DATA_DIR / "downloads" / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        
        # Usar configuraciones personalizadas o las por defecto
        self.browser_config = browser_config or BROWSER_CONFIG
        self.scraper_config = scraper_config or SCRAPER_CONFIG
        
        # Log de configuración actual
        logger.info(f"Configuración del navegador: headless={self.browser_config.get('headless', True)}")
        logger.info(f"Configuración de timeouts: {self.scraper_config.get('timeout', 60000)}ms")
        
    async def __aenter__(self):
        """Context manager entry"""
        await self.start_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close_browser()
    
    async def start_browser(self):
        """Inicializar el navegador"""
        logger.info("Iniciando navegador...")
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(**self.browser_config)
        
        # Crear contexto con configuración de descarga
        context = await self.browser.new_context(
            accept_downloads=True,
            locale="es-CL"  # Configurar idioma chileno
        )
        
        self.page = await context.new_page()
        
        # Configurar timeouts usando la configuración personalizada
        self.page.set_default_timeout(self.scraper_config["timeout"])
        
        logger.info("Navegador iniciado correctamente")
    
    async def close_browser(self):
        """Cerrar el navegador"""
        if self.browser:
            try:
                await self.browser.close()
                logger.info("Navegador cerrado")
            except:
                pass
    
    async def navigate_to_site(self):
        """Navegar al sitio INE.Stat"""
        logger.info(f"Navegando a {BASE_URL}")
        
        try:
            await self.page.goto(BASE_URL, wait_until="networkidle")
            logger.info("Sitio cargado correctamente")
            
            # Esperar a que la página esté completamente cargada
            possible_selectors = [
                "text=Datos por tema",
                "text=Data by topic", 
                "[class*='sidebar']",
                "[class*='menu']",
                "h1",
                ".main-content",
                "#main"
            ]
            
            selector_found = None
            for selector in possible_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    selector_found = selector
                    logger.info(f"Página cargada - Selector encontrado: {selector}")
                    break
                except:
                    logger.debug(f"Selector no encontrado: {selector}")
                    continue
            
            if not selector_found:
                await asyncio.sleep(5)
                logger.warning("No se encontraron selectores específicos, continuando...")
            
            # Capturar screenshot para debug
            await self.page.screenshot(path=self.downloads_dir / "debug_page_load.png")
            logger.info(f"Screenshot guardado en: {self.downloads_dir}/debug_page_load.png")
            
        except Exception as e:
            logger.error(f"Error al navegar al sitio: {e}")
            try:
                await self.page.screenshot(path=self.downloads_dir / "error_page_load.png")
            except:
                pass
            raise
    
    async def debug_page_structure(self):
        """Método de debug para ver la estructura de la página"""
        logger.info("=== DEBUG: Analizando estructura de la página ===")
        
        try:
            spans = await self.page.locator("span").all()
            logger.info(f"Total de spans encontrados: {len(spans)}")
            
            for i, span in enumerate(spans[:20]):
                text = await span.text_content()
                if text and ("VBA" in text or "Módulo" in text or "Estado" in text):
                    logger.info(f"Span {i}: '{text}'")
            
            tree_items = await self.page.locator(".treeview span").all()
            logger.info(f"Items en treeview: {len(tree_items)}")
            
            for i, item in enumerate(tree_items[:15]):
                text = await item.text_content()
                if text and text.strip():
                    logger.info(f"TreeView {i}: '{text.strip()}'")
            
            env_items = await self.page.locator("span").filter(has_text="Estadísticas de Medio Ambiente").all()
            logger.info(f"Items de Medio Ambiente encontrados: {len(env_items)}")
            
        except Exception as e:
            logger.error(f"Error en debug: {e}")
    
    async def expand_module_section(self, module_name: str):
        """Expandir una sección específica del módulo"""
        logger.info(f"Expandiendo sección: {module_name}")
        
        await self.debug_page_structure()
        
        try:
            module_locator = self.page.locator(f"span").filter(has_text=module_name)
            count = await module_locator.count()
            logger.info(f"Módulos encontrados con texto exacto: {count}")
            
            if count > 0:
                first_match = module_locator.first
                is_visible = await first_match.is_visible()
                logger.info(f"Elemento visible: {is_visible}")
                
                if not is_visible:
                    logger.info("Elemento no visible, buscando elemento padre para expandir...")
                    parent_li = first_match.locator("xpath=ancestor::li[@class='t closed' or @class='t opened']").first
                    parent_count = await parent_li.count()
                    
                    if parent_count > 0:
                        parent_span = parent_li.locator("span").first
                        parent_text = await parent_span.text_content()
                        logger.info(f"Expandiendo elemento padre: '{parent_text}'")
                        
                        await parent_span.click()
                        await asyncio.sleep(3)
                        
                        is_visible_now = await first_match.is_visible()
                        logger.info(f"Elemento visible después de expandir padre: {is_visible_now}")
                
                if await first_match.is_visible():
                    await first_match.click()
                    await asyncio.sleep(3)
                    logger.info(f"Módulo expandido exitosamente: {module_name}")
                    return True
                else:
                    logger.warning(f"Módulo aún no visible después de expandir padre: {module_name}")
                    return False
            
            # Estrategia alternativa: buscar por partes del nombre
            if "Aire" in module_name:
                air_locator = self.page.locator("span").filter(has_text="Aire")
                air_count = await air_locator.count()
                logger.info(f"Elementos con 'Aire': {air_count}")
                
                for i in range(air_count):
                    air_element = air_locator.nth(i)
                    if await air_element.is_visible():
                        await air_element.click()
                        await asyncio.sleep(3)
                        return True
            
            if "Agua" in module_name:
                water_locator = self.page.locator("span").filter(has_text="Agua")
                water_count = await water_locator.count()
                logger.info(f"Elementos con 'Agua': {water_count}")
                
                for i in range(water_count):
                    water_element = water_locator.nth(i)
                    if await water_element.is_visible():
                        await water_element.click()
                        await asyncio.sleep(3)
                        return True
            
            logger.warning(f"Módulo no encontrado o no clickeable: {module_name}")
            return False
                
        except Exception as e:
            logger.error(f"Error al expandir módulo {module_name}: {e}")
            return False
    
    async def select_dataset(self, dataset_name: str):
        """Seleccionar un dataset específico"""
        logger.info(f"Seleccionando dataset: {dataset_name}")
        
        try:
            # Verificar que el navegador y la página siguen activos
            if not self.page or self.page.is_closed():
                logger.warning("La página se cerró, saltando este dataset")
                return False
            
            # Primero cerrar cualquier modal que pueda estar abierto
            await self.force_close_all_modals()
            
            # Buscar link del dataset por texto exacto
            dataset_locator = self.page.locator(f"a.ds:has-text('{dataset_name}')")
            
            if await dataset_locator.count() > 0:
                await dataset_locator.click()
                
                # Esperar a que cargue la tabla de datos
                await self.page.wait_for_selector("table", timeout=20000)
                await asyncio.sleep(3)
                
                logger.info(f"Dataset seleccionado: {dataset_name}")
                return True
            else:
                logger.warning(f"Dataset no encontrado: {dataset_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error al seleccionar dataset {dataset_name}: {e}")
            
            # Si el error indica que el navegador se cerró, saltear
            if "Target page, context or browser has been closed" in str(e):
                logger.warning("Navegador cerrado inesperadamente, saltando este dataset")
                return False
            
            return False
    
    async def download_csv(self, dataset_name: str) -> Optional[str]:
        """Descargar CSV del dataset actual"""
        logger.info(f"Descargando CSV para: {dataset_name}")
        
        try:
            # Primero cerrar cualquier modal abierto
            await self.force_close_all_modals()
            
            # Buscar el botón de exportar
            export_button = self.page.locator("text=Exportar")
            if await export_button.count() == 0:
                logger.error("Botón Exportar no encontrado")
                return None
            
            # Hacer hover y click en CSV
            logger.info("Haciendo hover sobre el botón Exportar...")
            await export_button.hover()
            await asyncio.sleep(2)
            
            # Buscar opción CSV
            csv_options = [
                "text=Text file (CSV)",
                "text=Archivo de texto (CSV)", 
                "text=CSV"
            ]
            
            csv_clicked = False
            for csv_option in csv_options:
                try:
                    csv_locator = self.page.locator(csv_option)
                    if await csv_locator.count() > 0 and await csv_locator.first.is_visible():
                        logger.info(f"Seleccionando opción CSV: {csv_option}")
                        await csv_locator.first.click()
                        csv_clicked = True
                        break
                except Exception as e:
                    logger.debug(f"No se pudo usar selector {csv_option}: {e}")
                    continue
            
            if not csv_clicked:
                logger.warning("No se encontró opción CSV, intentando click directo en Exportar")
                await export_button.click()
            
            # Esperar a que aparezca el modal
            logger.info("Esperando que aparezca el modal de exportación...")
            await asyncio.sleep(3)
            
            # ESTRATEGIA 1: Esperar dinámicamente a que aparezca el iframe
            logger.info("=== ESTRATEGIA 1: Esperando iframe dinámico ===")
            iframe_found = await self.wait_for_dynamic_iframe()
            
            if iframe_found:
                result = await self.handle_iframe_download(iframe_found, dataset_name)
                if result:
                    await self.force_close_all_modals()
                    return result
            
            # ESTRATEGIA 2: Intentar descarga sin iframe (directa)
            logger.info("=== ESTRATEGIA 2: Descarga directa sin iframe ===")
            result = await self.try_direct_download_strategies(dataset_name)
            if result:
                await self.force_close_all_modals()
                return result
            
            # ESTRATEGIA 3: Manipulación JavaScript del modal
            logger.info("=== ESTRATEGIA 3: Manipulación JavaScript ===")
            result = await self.try_javascript_download_strategies(dataset_name)
            if result:
                await self.force_close_all_modals()
                return result
            
            logger.error("Todas las estrategias de descarga fallaron")
            await self.force_close_all_modals()
            return None
            
        except Exception as e:
            logger.error(f"Error al descargar CSV para {dataset_name}: {e}")
            await self.force_close_all_modals()
            try:
                await self.page.screenshot(path=self.downloads_dir / f"download_error_{dataset_name.replace(' ', '_')}.png")
            except:
                pass
            return None
    
    async def wait_for_dynamic_iframe(self, max_wait_time: int = 15) -> Optional:
        """Esperar a que aparezca dinámicamente el iframe"""
        logger.info("Esperando que se cargue el iframe dinámicamente...")
        
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
            try:
                # Buscar iframes que puedan haber aparecido
                iframe_selectors = [
                    "iframe[id='DialogFrame']",
                    "iframe[src*='modalexports']",
                    "iframe[src*='export']",
                    "#DialogFrame",
                    "iframe"
                ]
                
                for selector in iframe_selectors:
                    try:
                        iframes = await self.page.locator(selector).all()
                        logger.info(f"Buscando iframes con '{selector}': {len(iframes)} encontrados")
                        
                        for i, iframe in enumerate(iframes):
                            try:
                                # Verificar si el iframe está cargado y tiene contenido
                                frame_content = await iframe.content_frame()
                                if frame_content:
                                    # Esperar un poco más para que se cargue el contenido
                                    await asyncio.sleep(1)
                                    
                                    # Verificar si contiene elementos de descarga
                                    download_elements = await frame_content.locator("input, button").count()
                                    logger.info(f"Iframe {i}: {download_elements} elementos interactivos encontrados")
                                    
                                    if download_elements > 0:
                                        logger.info(f"Iframe válido encontrado: {selector}[{i}]")
                                        return frame_content
                                        
                            except Exception as e:
                                logger.debug(f"Error verificando iframe {i}: {e}")
                                continue
                                
                    except Exception as e:
                        logger.debug(f"Error con selector {selector}: {e}")
                        continue
                
                # Si no encontró iframe, esperar un poco más
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.debug(f"Error en ciclo de espera: {e}")
                await asyncio.sleep(0.5)
        
        logger.warning("No se encontró iframe dinámico después de esperar")
        return None
    
    async def handle_iframe_download(self, iframe_content, dataset_name: str) -> Optional[str]:
        """Manejar la descarga desde el iframe"""
        logger.info("Manejando descarga desde iframe...")
        
        try:
            # Debug del contenido del iframe
            await self.debug_iframe_content(iframe_content)
            
            # Estrategias específicas para el iframe
            download_selectors = [
                "input[value*='Descargar']",
                "input[value*='Download']", 
                "button:has-text('Descargar')",
                "button:has-text('Download')",
                "input[type='button']",
                "input[type='submit']",
                "button[type='submit']",
                "button",
                "*[onclick*='download']",
                "*[onclick*='export']"
            ]
            
            # Configurar listener de descarga
            async with self.page.expect_download(timeout=30000) as download_info:
                download_triggered = False
                
                for selector in download_selectors:
                    try:
                        elements = await iframe_content.locator(selector).all()
                        logger.info(f"Iframe selector '{selector}': {len(elements)} elementos")
                        
                        for i, element in enumerate(elements):
                            try:
                                is_visible = await element.is_visible()
                                is_enabled = await element.is_enabled()
                                
                                if is_visible and is_enabled:
                                    logger.info(f"Haciendo click en iframe elemento: {selector}[{i}]")
                                    await element.click()
                                    download_triggered = True
                                    break
                                    
                            except Exception as e:
                                logger.debug(f"Error con elemento {i}: {e}")
                                continue
                        
                        if download_triggered:
                            break
                            
                    except Exception as e:
                        logger.debug(f"Error con selector iframe {selector}: {e}")
                        continue
                
                if download_triggered:
                    download = await download_info.value
                    return await self.save_download(download, dataset_name)
                else:
                    # Intentar con JavaScript en el iframe
                    js_commands = [
                        "document.querySelector('input[value*=\"Descargar\"]')?.click()",
                        "document.querySelector('input[type=\"button\"]')?.click()",
                        "document.querySelector('button')?.click()",
                        "document.forms[0]?.submit()",
                        "[...document.querySelectorAll('*')].find(el => el.onclick && el.onclick.toString().includes('download'))?.click()"
                    ]
                    
                    for js_cmd in js_commands:
                        try:
                            logger.info(f"Ejecutando JavaScript en iframe: {js_cmd}")
                            await iframe_content.evaluate(js_cmd)
                            await asyncio.sleep(1)
                            
                            # Verificar si se inició descarga
                            try:
                                download = await download_info.value
                                logger.info("Descarga iniciada con JavaScript!")
                                return await self.save_download(download, dataset_name)
                            except:
                                continue
                                
                        except Exception as e:
                            logger.debug(f"Error con JavaScript: {e}")
                            continue
                
        except Exception as e:
            logger.error(f"Error manejando iframe: {e}")
        
        return None
    
    async def try_direct_download_strategies(self, dataset_name: str) -> Optional[str]:
        """Intentar descarga directa sin iframe"""
        logger.info("Intentando estrategias de descarga directa...")
        
        try:
            # Buscar botones de descarga en la página principal
            download_selectors = [
                "input[value*='Descargar']",
                "button:has-text('Descargar')",
                "text=Descargar",
                "*[onclick*='download']",
                "*[onclick*='export']",
                ".download-button",
                "#download",
                "#export"
            ]
            
            for selector in download_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    if len(elements) > 0:
                        logger.info(f"Encontrados {len(elements)} elementos con selector: {selector}")
                        
                        for i, element in enumerate(elements):
                            try:
                                if await element.is_visible() and await element.is_enabled():
                                    logger.info(f"Intentando descarga directa con: {selector}[{i}]")
                                    
                                    async with self.page.expect_download(timeout=15000) as download_info:
                                        await element.click()
                                        download = await download_info.value
                                        return await self.save_download(download, dataset_name)
                                        
                            except Exception as e:
                                logger.debug(f"Error con elemento directo {i}: {e}")
                                continue
                                
                except Exception as e:
                    logger.debug(f"Error con selector directo {selector}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error en descarga directa: {e}")
        
        return None
    
    async def try_javascript_download_strategies(self, dataset_name: str) -> Optional[str]:
        """Intentar descarga usando JavaScript"""
        logger.info("Intentando estrategias JavaScript...")
        
        try:
            js_strategies = [
                # Buscar y hacer click en elementos de descarga
                """
                const downloadBtn = document.querySelector('input[value*="Descargar"]') || 
                                   document.querySelector('button:contains("Descargar")') ||
                                   document.querySelector('*[onclick*="download"]');
                if (downloadBtn) downloadBtn.click();
                """,
                
                # Enviar formularios que puedan existir
                """
                const forms = document.querySelectorAll('form');
                forms.forEach(form => {
                    if (form.action && form.action.includes('export')) {
                        form.submit();
                    }
                });
                """,
                
                # Buscar en todos los iframes disponibles
                """
                const iframes = document.querySelectorAll('iframe');
                iframes.forEach(iframe => {
                    try {
                        const doc = iframe.contentDocument || iframe.contentWindow.document;
                        const downloadBtn = doc.querySelector('input[value*="Descargar"]') ||
                                          doc.querySelector('button') ||
                                          doc.querySelector('input[type="button"]');
                        if (downloadBtn) downloadBtn.click();
                    } catch(e) {}
                });
                """,
                
                # Trigger eventos de descarga
                """
                window.dispatchEvent(new Event('download'));
                document.dispatchEvent(new Event('export'));
                """
            ]
            
            for i, js_code in enumerate(js_strategies):
                try:
                    logger.info(f"Ejecutando estrategia JavaScript {i+1}")
                    
                    async with self.page.expect_download(timeout=10000) as download_info:
                        await self.page.evaluate(js_code)
                        await asyncio.sleep(2)
                        
                        download = await download_info.value
                        logger.info(f"Descarga exitosa con JavaScript estrategia {i+1}!")
                        return await self.save_download(download, dataset_name)
                        
                except Exception as e:
                    logger.debug(f"Error con estrategia JS {i+1}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error en estrategias JavaScript: {e}")
        
        return None
    
    async def force_close_all_modals(self):
        """Forzar el cierre de todos los modales abiertos (versión optimizada)"""
        logger.info("Cerrando modales...")
        
        try:
            # Estrategia 1: Presionar Escape (más rápido)
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
            
            # Estrategia 2: Remover overlays problemáticos con JavaScript
            await self.page.evaluate("""
                // Remover overlays que bloquean clicks
                document.querySelectorAll('.ui-widget-overlay').forEach(el => el.remove());
                document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
                
                // Cerrar diálogos jQuery UI
                if (typeof $ !== 'undefined') {
                    $('.ui-dialog').dialog('close');
                }
                
                // Remover cualquier elemento con position fixed que pueda ser overlay
                document.querySelectorAll('[class*="overlay"]').forEach(el => {
                    if (el.style.position === 'fixed' || el.style.position === 'absolute') {
                        el.style.display = 'none';
                    }
                });
            """)
            
            # Estrategia 3: Buscar botones de cierre solo si es necesario
            close_selectors = [
                ".ui-dialog-titlebar-close",
                ".ui-icon-closethick", 
                "[title='close']"
            ]
            
            for selector in close_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    if len(elements) > 0:
                        for element in elements:
                            if await element.is_visible():
                                await element.click()
                                break
                        break  # Si encontró y clickeó uno, salir del loop
                except:
                    continue
            
            await asyncio.sleep(1)
            logger.info("Modales cerrados")
            
        except Exception as e:
            logger.debug(f"Error cerrando modales: {e}")
            # Si falla, al menos intentar Escape de nuevo
            try:
                await self.page.keyboard.press("Escape")
            except:
                pass
    
    async def debug_iframe_content(self, iframe_content):
        """Debug detallado del contenido del iframe"""
        logger.info("=== DEBUG: Contenido del iframe ===")
        
        try:
            # Buscar todos los elementos
            all_inputs = await iframe_content.locator("input").all()
            logger.info(f"Inputs en iframe: {len(all_inputs)}")
            
            for i, input_elem in enumerate(all_inputs):
                try:
                    input_type = await input_elem.get_attribute("type")
                    input_value = await input_elem.get_attribute("value") 
                    is_visible = await input_elem.is_visible()
                    is_enabled = await input_elem.is_enabled()
                    logger.info(f"  Input {i}: type='{input_type}', value='{input_value}', visible={is_visible}, enabled={is_enabled}")
                except Exception as e:
                    logger.debug(f"Error con input {i}: {e}")
            
            all_buttons = await iframe_content.locator("button").all()
            logger.info(f"Buttons en iframe: {len(all_buttons)}")
            
            for i, button_elem in enumerate(all_buttons):
                try:
                    button_text = await button_elem.text_content()
                    is_visible = await button_elem.is_visible()
                    is_enabled = await button_elem.is_enabled()
                    logger.info(f"  Button {i}: text='{button_text}', visible={is_visible}, enabled={is_enabled}")
                except Exception as e:
                    logger.debug(f"Error con button {i}: {e}")
                    
        except Exception as e:
            logger.error(f"Error debuggeando iframe: {e}")
    
    async def save_download(self, download, dataset_name: str) -> str:
        """Guardar el archivo descargado"""
        safe_name = dataset_name.replace(" ", "_").replace("(", "").replace(")", "").replace(",", "")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.csv"
        
        file_path = self.downloads_dir / filename
        await download.save_as(file_path)
        
        logger.info(f"CSV descargado exitosamente: {file_path}")
        return str(file_path)
    
    async def scrape_module(self, module_key: str) -> List[str]:
        """Hacer scraping de un módulo completo"""
        module_info = MODULES_TO_SCRAPE[module_key]
        module_name = module_info["name"]
        datasets = module_info["datasets"]
        
        logger.info(f"Iniciando scraping del módulo: {module_name}")
        downloaded_files = []
        
        try:
            # Expandir el módulo
            if not await self.expand_module_section(module_name):
                logger.error(f"No se pudo expandir el módulo: {module_name}")
                return downloaded_files
            
            # Procesar cada dataset
            for dataset in datasets:
                logger.info(f"Procesando dataset: {dataset}")
                
                try:
                    # Seleccionar dataset
                    if await self.select_dataset(dataset):
                        # Descargar CSV
                        file_path = await self.download_csv(dataset)
                        if file_path:
                            downloaded_files.append(file_path)
                        
                        # Delay entre descargas
                        await asyncio.sleep(self.scraper_config["delay_between_requests"])
                    
                except Exception as e:
                    logger.error(f"Error procesando dataset {dataset}: {e}")
                    continue
            
            logger.info(f"Módulo {module_name} completado. Archivos descargados: {len(downloaded_files)}")
            
        except Exception as e:
            logger.error(f"Error en módulo {module_name}: {e}")
        
        return downloaded_files
    
    async def scrape_all_modules(self) -> Dict[str, List[str]]:
        """Hacer scraping de todos los módulos configurados"""
        logger.info("Iniciando scraping completo de módulos de Agua y Aire")
        
        all_downloads = {}
        
        try:
            await self.navigate_to_site()
            
            for module_key in MODULES_TO_SCRAPE.keys():
                logger.info(f"Procesando módulo: {module_key}")
                
                downloads = await self.scrape_module(module_key)
                all_downloads[module_key] = downloads
                
                # Delay entre módulos
                await asyncio.sleep(self.scraper_config["delay_between_requests"] * 2)
            
            logger.info("Scraping completo terminado")
            
        except Exception as e:
            logger.error(f"Error en scraping completo: {e}")
            raise
        
        return all_downloads

    def generate_summary_report(self, downloads: Dict[str, List[str]]):
        """Generar reporte resumen de la ejecución"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report_lines = [
            "="*60,
            f"REPORTE DE SCRAPING INE.STAT - {timestamp}",
            "="*60,
            f"Directorio de descargas: {self.downloads_dir}",
            ""
        ]
        
        total_files = 0
        for module, files in downloads.items():
            module_info = MODULES_TO_SCRAPE[module]
            report_lines.extend([
                f"Módulo: {module_info['name']}",
                f"Archivos descargados: {len(files)}",
                ""
            ])
            
            for file_path in files:
                filename = Path(file_path).name
                report_lines.append(f"  - {filename}")
            
            report_lines.append("")
            total_files += len(files)
        
        report_lines.extend([
            f"TOTAL DE ARCHIVOS DESCARGADOS: {total_files}",
            "="*60
        ])
        
        # Guardar reporte
        report_path = self.downloads_dir / "scraping_report.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        
        # Mostrar en consola
        for line in report_lines:
            logger.info(line)
        
        return report_path