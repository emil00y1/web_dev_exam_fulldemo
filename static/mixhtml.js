function cl(text){console.log(text)}

// Attempt to set up Single Page App functionality
try{
    history.replaceState({"mixonurl":mix_replace_url}, "title", mix_replace_url)
}catch(err){
    cl(`Single Page App not possible, since mix_replace_url not set`)
}

// Main entry point for handling mix-html interactions
async function mixhtml(el=false){
    if(!el){
        el = event.target
    }

    let url = ""
    if(el.hasAttribute("mix-get")){ url = el.getAttribute("mix-get") }
    if(el.hasAttribute("mix-post")){ url = el.getAttribute("mix-post") }
    if(el.hasAttribute("mix-put")){ url = el.getAttribute("mix-put") }
    if(el.hasAttribute("mix-delete")){ url = el.getAttribute("mix-delete") }
    if(url == ""){ cl(`mix-method missing, therefore url not found`); return }
    cl(`url: ${url}`)

    // Check if content is already loaded for this URL
    if(document.querySelector(`[mix-on-url="${url}"]`)){
        cl("SPA already loaded, showing elements")
        mixonurl(url)
        return
    }

    mix_fetch_data(el)
}

// Core function for handling data fetching and validation
async function mix_fetch_data(el){
    let method = ""
    if(el.hasAttribute("mix-get")){ method = "get" }
    if(el.hasAttribute("mix-post")){ method = "post" }
    if(el.hasAttribute("mix-put")){ method = "put" }
    if(el.hasAttribute("mix-delete")){ method = "delete" }
    
    let url = el.getAttribute("mix-"+method).includes("?") ? 
        `${el.getAttribute("mix-"+method)}&spa=yes` : 
        `${el.getAttribute("mix-"+method)}?spa=yes` 
    
    if(method == "post" || method == "put"){
        if(!el.getAttribute("mix-data")){cl(`error : mix_fetch_data() mix-data missing`); return}
        if(!document.querySelector(el.getAttribute("mix-data"))){cl(`error - mix-data element doesn't exist`); return} 
        const frm = document.querySelector(el.getAttribute("mix-data"))
        
        // Clear existing error messages before validation
        frm.querySelectorAll('.error-msg').forEach(msg => {
            msg.textContent = ''
            msg.classList.add('hidden')
        })

        // Form validation
        let errors = false
        const attrs = frm.querySelectorAll("[mix-check]")
        for(let i = 0; i < attrs.length; i++){
            const input = attrs[i]

            if(input.closest('.d-none')) continue;

            input.classList.remove("border-c-red:-6") 
            const regex = input.getAttribute("mix-check")
            re = new RegExp(regex)
            cl(re.test(input.value))
            if(!re.test(input.value)){
                cl("mix-check failed")
                input.classList.add("border-c-red:-6")
                
                // Handle custom error message display
                const errorMessage = input.getAttribute('mix-error') || 'Invalid input'
                let errorContainer = input.parentElement.querySelector('.error-msg')
                if(!errorContainer){
                    errorContainer = document.createElement('span')
                    errorContainer.className = 'error-msg text-c-red:-6 text-sm mt-1'
                    input.parentElement.appendChild(errorContainer)
                }
                errorContainer.textContent = errorMessage
                errorContainer.classList.remove('hidden')
                
                errors = true
            }
        }  
        if(errors) return
    }   
    
    // Handle loading states
    if(el.getAttribute("mix-await")){
        el.disabled = true
        el.innerHTML = el.getAttribute("mix-await")
    }    

    if(el.getAttribute("mix-wait")){
        el.classList.add("mix-hidden")
        document.querySelector(el.getAttribute("mix-wait")).classList.remove("mix-hidden")
    }

    // Perform the actual fetch request
    let conn = null
    if(["post", "put", "patch"].includes(method)){
        conn = await fetch(url, {
            method: method,
            body: new FormData(document.querySelector(el.getAttribute("mix-data")))
        })        
    }else{   
        conn = await fetch(url, {
            method: method
        })
    }

    // Reset loading states
    if(el.getAttribute("mix-await")){
        el.disabled = false
        el.innerHTML = el.getAttribute("mix-default")
    }    

    if(el.getAttribute("mix-wait")){
        el.classList.remove("mix-hidden")
        document.querySelector(el.getAttribute("mix-wait")).classList.add("mix-hidden")
    }    

    // Process the response
    res = await conn.text()
    document.querySelector("body").insertAdjacentHTML('beforeend', res)
    process_template(el.getAttribute("mix-"+method))
}

// Process template responses
function process_template(mix_url){
    cl(`process_template() mix-url ${mix_url}`) 

    let new_url = false 
    
    if(document.querySelector("template[mix-redirect]")){ 
        cl(`mix-redirect found`)
        location.href = document.querySelector("template[mix-redirect]").getAttribute("mix-redirect")
        return 
    }

    if(!document.querySelector("template[mix-target]") && !document.querySelector("template[mix-function]")){ 
        cl(`error = mix-target nor mix-function found`)
        return 
    }

    document.querySelectorAll('template[mix-target]').forEach(template => {
        if(template.getAttribute("mix-newurl") && new_url == false){
            new_url = template.getAttribute("mix-newurl")
        }

        if(!template.getAttribute("mix-target")){console.log(`process_template() - error - mix-target missing`); return}    
        console.log(`ok : mix() the response data will affect '${template.getAttribute("mix-target")}'`)
        if(!document.querySelector(template.getAttribute("mix-target"))){console.log(`process_template() - error - mix-target is not in the dom`); return}   

        let position = "innerHTML"
        if(template.hasAttribute('mix-before')){position = "beforebegin"}
        if(template.hasAttribute("mix-after")){position = "afterend"}
        if(template.hasAttribute("mix-top")){position = "afterbegin"}
        if(template.hasAttribute("mix-bottom")){position = "beforeend"}
        if(template.hasAttribute("mix-replace")){position = "replace"}
        
        if(position == "innerHTML"){            
            document.querySelector(template.getAttribute("mix-target")).innerHTML = template.innerHTML
        }
        else if(position == "replace"){
            document.querySelector(template.getAttribute("mix-target")).insertAdjacentHTML("afterend", template.innerHTML)
            document.querySelector(template.getAttribute("mix-target")).remove()            
        }
        else{
            document.querySelector(template.getAttribute("mix-target")).insertAdjacentHTML(position, template.innerHTML)
        }        

        if(!template.getAttribute("mix-push-url")){cl(`process_template() - optional - mix-push-url not set`)}
        template.remove()
        mix_convert();
        mixonurl(mix_url)
    })

    document.querySelectorAll('template[mix-function]').forEach(template => {
        function_name = template.getAttribute("mix-function")
        console.log(`ok : mix() the response data will run the function '${function_name}'`)
        window[function_name](template.innerHTML)
        template.remove()
    })    
}

// Handle URL-based content display
function mixonurl(mix_url, push_to_history = true){
    document.querySelectorAll(`[mix-on-url='${mix_url}']`).forEach(el => {
        const title = el.getAttribute("mix-title") || false
        if(title){ document.title = title}   

        if(el.getAttribute("mix-push-url") && push_to_history){
            cl("Pushing to history")
            history.pushState({"mixonurl":el.getAttribute("mix-push-url")}, "", el.getAttribute("mix-push-url"))
        }

        if(el.getAttribute("mix-hide")){
            document.querySelectorAll(el.getAttribute("mix-hide")).forEach(i => {
                i.classList.add("hidden")
            })
        }
        if(el.getAttribute("mix-show")){
            document.querySelectorAll(el.getAttribute("mix-show")).forEach(i => {
                i.classList.remove("hidden")
            })
        }            
    })
}

// Handle browser back/forward navigation
window.onpopstate = function(event){
    cl(`##### onpopstate`)
    cl(event.state.mixonurl)
    mixonurl(event.state.mixonurl, false)
}

// Handle time-to-live elements
setInterval(function(){
    document.querySelectorAll("[mix-ttl]").forEach(el=>{
        if(el.getAttribute("mix-ttl") <= 0){
            el.remove()
        }else{
            el.setAttribute("mix-ttl", el.getAttribute("mix-ttl") - 1000)
        }
    })
}, 500)

// Convert elements with mix attributes to have proper event handlers
function mix_convert(){
    document.querySelectorAll("[mix-get], [mix-delete], [mix-put], [mix-post]").forEach(el => {
        let method = "mix-get"
        if(el.hasAttribute("mix-delete")){ method = "mix-delete" }
        
        let url = ""
        if(el.getAttribute(method) == ""){    
            if(el.getAttribute("href")){
                el.setAttribute(`${method}`, el.getAttribute("href"))
            }
            if(el.getAttribute("action")){
                el.setAttribute(`${method}`, el.getAttribute("action"))
            }                            
        }
        if(!el.hasAttribute("mix-focus") && !el.hasAttribute("mix-blur")){
            el.setAttribute("onclick", "mixhtml(); return false")
        }
    })  

    let mix_event = "onclick"
    document.querySelectorAll("[mix-focus], [mix-blur]").forEach(el => {
        if(el.hasAttribute("mix-focus")){ mix_event = "onfocus" }
        if(el.hasAttribute("mix-blur")){ mix_event = "onblur" }
        el.setAttribute(mix_event, "mixhtml(); return false")
    })     
}

// Initialize the conversion of mix elements
mix_convert();