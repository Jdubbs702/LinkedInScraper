# Define paths to all needed elements
paths_dict = {
    'show_more_path': '/html/body/main/section/div/div/section/div/div/section/button',
    'seniority_path': '/html/body/main/section/div/div/section/div/ul/li/span',
    'job_title_path': '/html/body/main/section/div/section[2]/div/div/div/h1',
    'company_name_path': '/html/body/main/section/div/section[2]/div/div/div/h4/div/span/a',
    'location_path': '/html/body/main/section/div/section[2]/div/div/div/h4/div/span[2]',
    'date_path': '/html/body/main/section/div/section[2]/div/div/div/h4/div[2]/span',
    'jd_parent_path': '/html/body/main/section/div/div/section/div/div/section'
}

getText_js = """
                const parent = arguments[0];
                const descendants = parent.childNodes;
                let text_list = [];
                for (let i = 0; i < descendants.length; i++) {
                    const element = descendants[i];
                    if (element.nodeType === Node.ELEMENT_NODE) {
                        const element_text = element.textContent.trim();
                        if (element_text !== '') {
                            text_list.push(element_text);
                        }
                    }
                }
                return text_list;
            """