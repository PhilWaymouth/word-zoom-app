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