const contentWrapper = document.getElementById('content-wrapper');
const definitionStack = [];

function getWordAndContext(event) {
    const selection = window.getSelection();
    let word = selection.toString().trim();
    let context = '';

    if (word) {
        const surroundingText = selection.anchorNode.textContent;
        context = surroundingText;
    } else {
        const range = document.caretRangeFromPoint(event.clientX, event.clientY);
        if (range) {
            const textNode = range.startContainer;
            const textContent = textNode.textContent;
            const offset = range.startOffset;

            let start = offset;
            while (start > 0 && !/\s/.test(textContent[start - 1])) {
                start--;
            }

            let end = offset;
            while (end < textContent.length && !/\s/.test(textContent[end])) {
                end++;
            }

            word = textContent.substring(start, end);
            context = textContent;
        }
    }

    return { word, context };
}

contentWrapper.addEventListener('wheel', function(event) {
    if (event.deltaY < 0) { // Zoom in
        const { word, context } = getWordAndContext(event);

        if (word) {
            const currentContent = contentWrapper.innerHTML;
            definitionStack.push(currentContent);

            htmx.ajax('GET', `/define?word=${word}&context=${context}`, {
                target: contentWrapper,
                swap: 'innerHTML'
            });
        }
    } else { // Zoom out
        if (definitionStack.length > 0) {
            const previousContent = definitionStack.pop();
            contentWrapper.innerHTML = previousContent;
        }
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const textInput = document.getElementById('text-input');
    let isDefining = false;
    let lastScrollTime = 0;
    const SCROLL_DEBOUNCE = 300;
    
    // Handle scroll wheel for word definition
    textInput.addEventListener('wheel', function(e) {
        const currentTime = Date.now();
        
        if (e.deltaY !== 0 && !isDefining && (currentTime - lastScrollTime) > SCROLL_DEBOUNCE) {
            const wordInfo = getWordAtPosition(e.clientX, e.clientY);
            if (wordInfo && wordInfo.word && wordInfo.word.length > 2) {
                e.preventDefault();
                lastScrollTime = currentTime;
                defineWordInline(wordInfo);
            }
        }
    });
    
    // Handle double-click for word definition
    textInput.addEventListener('dblclick', function(e) {
        if (isDefining) return;
        
        const selection = window.getSelection();
        if (selection.toString().trim()) {
            const range = selection.getRangeAt(0);
            const word = selection.toString().trim();
            defineWordInline({
                word: word,
                range: range,
                element: range.commonAncestorContainer
            });
        } else {
            const wordInfo = getWordAtPosition(e.clientX, e.clientY);
            if (wordInfo && wordInfo.word) {
                defineWordInline(wordInfo);
            }
        }
    });
    
    function getWordAtPosition(x, y) {
        const range = document.caretRangeFromPoint(x, y);
        if (!range) return null;
        
        let textNode = range.startContainer;
        let offset = range.startOffset;
        
        // If we're in an element node, try to find the text node
        if (textNode.nodeType === Node.ELEMENT_NODE) {
            const walker = document.createTreeWalker(
                textNode,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            let node;
            while (node = walker.nextNode()) {
                const nodeRange = document.createRange();
                nodeRange.selectNodeContents(node);
                const rect = nodeRange.getBoundingClientRect();
                if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
                    textNode = node;
                    // Approximate offset based on position
                    const relativeX = x - rect.left;
                    const charWidth = rect.width / node.textContent.length;
                    offset = Math.floor(relativeX / charWidth);
                    break;
                }
            }
        }
        
        if (textNode.nodeType !== Node.TEXT_NODE) return null;
        
        const text = textNode.textContent;
        let start = Math.min(offset, text.length - 1);
        let end = start;
        
        // Find word boundaries
        while (start > 0 && /\w/.test(text[start - 1])) start--;
        while (end < text.length && /\w/.test(text[end])) end++;
        
        const word = text.substring(start, end);
        if (word && word.length > 1) {
            const wordRange = document.createRange();
            wordRange.setStart(textNode, start);
            wordRange.setEnd(textNode, end);
            
            return {
                word: word,
                range: wordRange,
                element: textNode
            };
        }
        
        return null;
    }
    
    function defineWordInline(wordInfo) {
        if (!wordInfo || !wordInfo.word || wordInfo.word.length < 2) return;
        
        isDefining = true;
        console.log(`Defining word: ${wordInfo.word}`);
        
        // Start fade out
        textInput.classList.add('loading');
        
        // Highlight the word temporarily
        const originalWord = wordInfo.word;
        const span = document.createElement('span');
        span.className = 'defined-word';
        span.textContent = originalWord;
        
        // Create loading indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading-indicator';
        loadingDiv.textContent = `Defining "${originalWord}"...`;
        
        try {
            wordInfo.range.deleteContents();
            wordInfo.range.insertNode(span);
            
            // Insert loading indicator after the word
            const range = document.createRange();
            range.setStartAfter(span);
            range.insertNode(loadingDiv);
            range.setStartAfter(loadingDiv);
            range.insertNode(document.createTextNode('\n'));
        } catch (e) {
            console.error('Error highlighting word:', e);
        }
        
        // Get the full text content for context
        const context = textInput.textContent || textInput.innerText;
        
        // Make API request
        fetch(`/define?word=${encodeURIComponent(originalWord)}&context=${encodeURIComponent(context)}`)
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const definition = doc.body.textContent || doc.body.innerText || '';
                
                // Remove loading indicator
                loadingDiv.remove();
                
                // Create definition element
                const definitionDiv = document.createElement('div');
                definitionDiv.className = 'word-definition';
                definitionDiv.innerHTML = `
                    <strong>"${originalWord}":</strong> ${definition}
                    <button class="close-btn" onclick="this.parentElement.remove(); return false;">×</button>
                `;
                
                // Insert definition after the word
                const range = document.createRange();
                range.setStartAfter(span);
                range.insertNode(definitionDiv);
                
                // Add some spacing
                range.setStartAfter(definitionDiv);
                range.insertNode(document.createTextNode('\n'));
                
                // Fade back in
                setTimeout(() => {
                    textInput.classList.remove('loading');
                }, 100);
                
            })
            .catch(error => {
                console.error('Error fetching definition:', error);
                
                // Remove loading indicator
                loadingDiv.remove();
                
                // Restore original word if there's an error
                span.replaceWith(document.createTextNode(originalWord));
                
                // Fade back in
                setTimeout(() => {
                    textInput.classList.remove('loading');
                }, 100);
            })
            .finally(() => {
                isDefining = false;
            });
    }
    
    // Handle paste to maintain plain text
    textInput.addEventListener('paste', function(e) {
        e.preventDefault();
        const text = (e.clipboardData || window.clipboardData).getData('text');
        document.execCommand('insertText', false, text);
    });
});