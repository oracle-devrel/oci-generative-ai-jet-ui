# Markdown Document Viewer Component

## Support Notice ##

> December 2023: **This sample component has been retired and will no longer be updated.**
>
> If you want to take a copy of this code for your own use see [Viewing the Source Code for the oj-sample Components](https://blogs.oracle.com/groundside/post/viewing-the-source-code-for-the-oj-sample-components)

----

The **`<oj-sample-markdown-viewer>`** provides a simple viewer which will take a string as a value and interprets markdown formatting for display.

The component supports interpreting markdown in several variants including the [GitHub Flavor of Markdown](https://help.github.com/articles/basic-writing-and-formatting-syntax/). This is controlled via the **flavor** property.

## Example

A sample markdown file might look a little like this

> \# Title  
> \## Subtitle  
> Normal paragraph text  
> \* Bullet Point 1  
> \* Bullet Point 2  
> \* Bullet Point 3  
> And a code block  
> \`\`\` JavaScript  
> var self = this;  
> \`\`\`  

Assuming the above file had been sucked into a JavaScript variable called markupToDisplay then the component would
simply look like this

``` JavaScript
<oj-sample-markdown-viewer value="[[markupToDisplay]]" output-filter="[[xssFilter]]"></oj-sample-markdown-viewer>
```

And the result in the UI would be:

> # Title  
> ## Subtitle  
> Normal paragraph text  
> * Bullet Point 1  
> * Bullet Point 2  
> * Bullet Point 3  
> And a code block  
> ``` JavaScript  
> var self = this;  
> ```  

## Notes

1. The **value** property is read-only.
2. Because markdown is a very flexible format it can be used to embed undesirable content into your page. If you are receiving the markdown string from an unknown source (such as an uploaded file) you must be careful to sanitize the HTML created by the conversion process in order to remove unwanted HTML or injected JavaScript. The output-filter function callback is provided for you to do so.  This function should take a string containing the candidate HTML output and should return a promise to the sanitized version.
3. This Custom Web Component uses a 3rd party library to manage the markdown conversion process. Currently this is [Marked 4.3.0](https://github.com/markedjs/marked)

## Support Information

This component is an unsupported sample for demonstration purposes only. If you encounter any problems feel free to report them via the Oracle forums and we will do our best to address them, however, note that this will be on a best-effort basis only.