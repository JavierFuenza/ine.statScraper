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
    
    async def discover_available_datasets(self, module_name: str) -> List[str]:
        """Descubrir automáticamente los datasets disponibles en un módulo específico"""
        logger.info(f"Descubriendo datasets disponibles en módulo: {module_name}")
        
        available_datasets = []
        
        try:
            # Expandir el módulo primero
            if not await self.expand_module_section(module_name):
                logger.error(f"No se pudo expandir el módulo: {module_name}")
                return available_datasets
            
            # Esperar a que se carguen los datasets
            await asyncio.sleep(3)
            
            # Buscar el elemento del módulo específico para delimitar la búsqueda
            module_locator = self.page.locator(f"span").filter(has_text=module_name)
            
            if await module_locator.count() == 0:
                logger.error(f"No se encontró el módulo: {module_name}")
                return available_datasets
            
            # Encontrar el contenedor padre del módulo (li element)
            module_li = module_locator.first.locator("xpath=ancestor::li[contains(@class, 't')]").first
            
            if await module_li.count() == 0:
                logger.error(f"No se encontró el contenedor del módulo: {module_name}")
                return available_datasets
            
            # Buscar SOLO los enlaces de datasets dentro de este módulo específico
            dataset_links = await module_li.locator("a.ds").all()
            logger.info(f"Enlaces de datasets encontrados en {module_name}: {len(dataset_links)}")
            
            for i, link in enumerate(dataset_links):
                try:
                    dataset_text = await link.text_content()
                    if dataset_text and dataset_text.strip():
                        clean_text = dataset_text.strip()
                        if clean_text not in available_datasets:
                            available_datasets.append(clean_text)
                            logger.info(f"Dataset descubierto {i+1}: '{clean_text}'")
                        
                except Exception as e:
                    logger.debug(f"Error procesando dataset link {i}: {e}")
                    continue
            
            logger.info(f"Total de datasets descubiertos en {module_name}: {len(available_datasets)}")
            
        except Exception as e:
            logger.error(f"Error descubriendo datasets en {module_name}: {e}")
        
        return available_datasets

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
            
            # Esperar a que aparezca el modal y se cargue el contenido dinámicamente
            logger.info("Esperando que aparezca el modal de exportación y se cargue el contenido...")
            
            # Esperar a que aparezca el contenido del diálogo dinámicamente
            try:
                await self.page.wait_for_selector("#dialog-content", timeout=10000)
                logger.info("Modal dialog-content encontrado")
                
                # Esperar un poco más para que se cargue el contenido interno
                await asyncio.sleep(3)
                
                # Verificar si hay contenido en el modal
                dialog_content = await self.page.locator("#dialog-content").text_content()
                dialog_html = await self.page.locator("#dialog-content").inner_html()
                logger.info(f"Contenido del modal dialog-content: '{dialog_content[:200]}...' (primeros 200 chars)")
                logger.info(f"HTML del modal dialog-content: '{dialog_html[:500]}...' (primeros 500 chars)")
                
                # También verificar si hay otros modales o dialogs activos
                all_visible_divs = await self.page.locator("div:visible").all()
                logger.info(f"Total de divs visibles en la página: {len(all_visible_divs)}")
                
                # Buscar cualquier elemento que contenga "Export" o "Descargar"
                export_elements = await self.page.locator("*:has-text('Export')").all()
                descargar_elements = await self.page.locator("*:has-text('Descargar')").all()
                generate_elements = await self.page.locator("*:has-text('Generate')").all()
                
                logger.info(f"Elementos con 'Export': {len(export_elements)}")
                logger.info(f"Elementos con 'Descargar': {len(descargar_elements)}")
                logger.info(f"Elementos con 'Generate': {len(generate_elements)}")
                
                # Si hay elementos con estos textos, mostrar información sobre ellos
                for i, elem in enumerate(export_elements[:3]):
                    try:
                        text = await elem.text_content()
                        is_visible = await elem.is_visible()
                        logger.info(f"Export elemento {i+1}: visible={is_visible}, text='{text[:100]}'")
                    except:
                        pass
                
            except Exception as e:
                logger.warning(f"No se pudo esperar a dialog-content: {e}")
                await asyncio.sleep(3)
            
            # ESTRATEGIA 1 (PRIORITARIA): Manipulación JavaScript del modal
            logger.info("=== ESTRATEGIA 1: Manipulación JavaScript (PRIORITARIA) ===")
            result = await self.try_javascript_download_strategies(dataset_name)
            if result:
                logger.info("JavaScript descarga exitosa, cerrando modales...")
                await self.force_close_all_modals()
                return result
            
            # ESTRATEGIA 2: Esperar dinámicamente a que aparezca el iframe
            logger.info("=== ESTRATEGIA 2: Esperando iframe dinámico ===")
            iframe_found = await self.wait_for_dynamic_iframe()
            
            if iframe_found:
                result = await self.handle_iframe_download(iframe_found, dataset_name)
                if result:
                    logger.info("Iframe descarga exitosa, cerrando modales...")
                    await self.force_close_all_modals()
                    return result
            
            # ESTRATEGIA 3: Intentar descarga sin iframe (directa)
            logger.info("=== ESTRATEGIA 3: Descarga directa sin iframe ===")
            result = await self.try_direct_download_strategies(dataset_name)
            if result:
                logger.info("Descarga directa exitosa, cerrando modales...")
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
        """Intentar descarga usando JavaScript - Buscar botón Descargar en modal dialog"""
        logger.info("Intentando encontrar botón Descargar en modal dialog...")
        
        try:
            # Basado en las screenshots, el botón Descargar está en un modal dialog, no iframe
            # Estrategias específicas para encontrar el botón "Descargar"
            
            download_selectors = [
                # Botones específicos dentro del dialog-content dinámico (lo más específico primero)
                "#dialog-content input[value='Descargar']",
                "#dialog-content button:has-text('Descargar')",
                "#dialog-content input[value*='Descargar']",
                "#dialog-content input[type='button']",
                "#dialog-content button[type='button']",
                "#dialog-content input[type='submit']",
                "#dialog-content button",
                
                # Botones dentro de modales jQuery UI
                ".ui-dialog input[value*='Descargar']",
                ".ui-dialog button:has-text('Descargar')",
                ".ui-dialog input[type='button']",
                ".ui-dialog button[type='button']",
                
                # Botones generales con texto "Descargar"
                "input[value='Descargar']",
                "button:has-text('Descargar')",
                "input[value*='Descargar']",
                
                # Fallback - cualquier botón visible
                "input[type='button']:visible",
                "button:visible"
            ]
            
            for i, selector in enumerate(download_selectors):
                try:
                    logger.info(f"Probando selector {i+1}/{len(download_selectors)}: {selector}")
                    
                    # Buscar elementos con este selector
                    elements = await self.page.locator(selector).all()
                    logger.info(f"Encontrados {len(elements)} elementos con selector: {selector}")
                    
                    for j, element in enumerate(elements):
                        try:
                            # Verificar si el elemento es visible y habilitado
                            if await element.is_visible() and await element.is_enabled():
                                text_content = await element.text_content() or ""
                                input_value = await element.get_attribute("value") or ""
                                logger.info(f"Elemento {j+1}: text='{text_content}', value='{input_value}', visible=True, enabled=True")
                                
                                # Intentar hacer click y descargar
                                async with self.page.expect_download(timeout=10000) as download_info:
                                    await element.click()
                                    logger.info(f"Haciendo click en elemento: {selector}[{j}]")
                                    await asyncio.sleep(2)
                                    
                                    download = await download_info.value
                                    logger.info(f"¡Descarga exitosa con selector {selector}!")
                                    return await self.save_download(download, dataset_name)
                            else:
                                text_content = await element.text_content() or ""
                                input_value = await element.get_attribute("value") or ""
                                is_visible = await element.is_visible()
                                is_enabled = await element.is_enabled()
                                logger.debug(f"Elemento {j+1} no clickeable: text='{text_content}', value='{input_value}', visible={is_visible}, enabled={is_enabled}")
                                
                        except Exception as e:
                            logger.debug(f"Error con elemento {j+1} del selector {selector}: {e}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error con selector {selector}: {e}")
                    continue
            
            # ESTRATEGIA ESPECÍFICA: Sabemos que hay un iframe DialogFrame en #dialog-content
            logger.info("Intentando acceso directo al iframe DialogFrame...")
            js_iframe_commands = [
                # Acceder al iframe DialogFrame específicamente
                """
                try {
                    const iframe = document.querySelector('#dialog-content iframe[id="DialogFrame"]') || document.querySelector('iframe[id="DialogFrame"]');
                    if (iframe && iframe.contentDocument) {
                        const doc = iframe.contentDocument;
                        const btn = doc.querySelector('input[value*="Descargar"]') || doc.querySelector('input[type="button"]') || doc.querySelector('button');
                        if (btn) { btn.click(); console.log('Clicked iframe button:', btn.value || btn.textContent); }
                    }
                } catch(e) { console.log('Error accessing iframe:', e); }
                """,
                
                # Intentar con contentWindow
                """
                try {
                    const iframe = document.querySelector('#dialog-content iframe[id="DialogFrame"]') || document.querySelector('iframe[id="DialogFrame"]');
                    if (iframe && iframe.contentWindow) {
                        const doc = iframe.contentWindow.document;
                        const btn = doc.querySelector('input[value*="Descargar"]') || doc.querySelector('input[type="button"]') || doc.querySelector('button');
                        if (btn) { btn.click(); console.log('Clicked iframe button via contentWindow:', btn.value || btn.textContent); }
                    }
                } catch(e) { console.log('Error accessing iframe via contentWindow:', e); }
                """
            ]
            
            for i, js_cmd in enumerate(js_iframe_commands):
                try:
                    logger.info(f"Ejecutando comando iframe JavaScript {i+1}/2")
                    
                    async with self.page.expect_download(timeout=10000) as download_info:
                        await self.page.evaluate(js_cmd)
                        await asyncio.sleep(3)
                        
                        download = await download_info.value
                        logger.info(f"¡Descarga exitosa con comando iframe JavaScript {i+1}!")
                        return await self.save_download(download, dataset_name)
                        
                except Exception as e:
                    logger.debug(f"Error comando iframe JavaScript {i+1}: {e}")
                    continue
            
            # Si no funcionaron los comandos específicos del iframe, intentar JavaScript directo
            logger.info("Intentando JavaScript directo como último recurso...")
            js_commands = [
                "document.querySelector('input[value=\"Descargar\"]')?.click()",
                "document.querySelector('button').click()", 
                "[...document.querySelectorAll('input')].find(el => el.value && el.value.includes('Descargar'))?.click()",
                "[...document.querySelectorAll('button')].find(el => el.textContent && el.textContent.includes('Descargar'))?.click()"
            ]
            
            for i, js_cmd in enumerate(js_commands):
                try:
                    logger.info(f"Ejecutando JavaScript directo {i+1}/4: {js_cmd}")
                    
                    async with self.page.expect_download(timeout=8000) as download_info:
                        await self.page.evaluate(js_cmd)
                        await asyncio.sleep(2)
                        
                        download = await download_info.value
                        logger.info(f"¡Descarga exitosa con JavaScript directo {i+1}!")
                        return await self.save_download(download, dataset_name)
                        
                except Exception as e:
                    logger.debug(f"Error JavaScript directo {i+1}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error en estrategias JavaScript: {e}")
        
        logger.warning("No se pudo encontrar o hacer click en el botón Descargar")
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
        configured_datasets = module_info["datasets"]
        
        logger.info(f"Iniciando scraping del módulo: {module_name}")
        downloaded_files = []
        
        try:
            # Determinar qué datasets usar
            datasets_to_process = configured_datasets
            
            # Si la configuración está vacía, descubrir datasets automáticamente
            if not configured_datasets:
                logger.info(f"Configuración de datasets vacía para {module_name}, descubriendo automáticamente...")
                datasets_to_process = await self.discover_available_datasets(module_name)
                
                if not datasets_to_process:
                    logger.warning(f"No se encontraron datasets para el módulo: {module_name}")
                    return downloaded_files
                
                logger.info(f"Se descubrieron {len(datasets_to_process)} datasets automáticamente")
            else:
                # Expandir el módulo para datasets configurados
                if not await self.expand_module_section(module_name):
                    logger.error(f"No se pudo expandir el módulo: {module_name}")
                    return downloaded_files
            
            # Procesar cada dataset
            for dataset in datasets_to_process:
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
            configured_datasets = module_info["datasets"]
            
            # Indicar si se usó auto-descubrimiento
            discovery_mode = "AUTO-DESCUBRIMIENTO" if not configured_datasets else "CONFIGURACIÓN PREDEFINIDA"
            
            report_lines.extend([
                f"Módulo: {module_info['name']}",
                f"Modo: {discovery_mode}",
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