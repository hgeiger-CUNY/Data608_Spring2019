library(ggplot2)
library(dplyr)
library(shiny)

df <- read.csv("https://raw.githubusercontent.com/charleyferrari/CUNY_DATA_608/master/module3/data/cleaned-cdc-mortality-1999-2010-2.csv",
        header=TRUE,stringsAsFactors=FALSE)

df <- df[df$ICD.Chapter != "Codes for special purposes" & df$ICD.Chapter != "Diseases of the ear and mastoid process",] #Remove causes found in very few years/states.

ui <- fluidPage(
	headerPanel('Mortality rates in 2010 across United States'),
	sidebarPanel(
		selectInput('cause','Cause of death',unique(df$ICD.Chapter),selected='Diseases of the circulatory system')
	),
	mainPanel(
		plotOutput('plot1')
	)
)

server <- function(input, output) {
	output$plot1 <- renderPlot({
		dfSlice <- df %>%
			filter(ICD.Chapter == input$cause,Year == 2010)

		dfSlice$State <- factor(dfSlice$State,levels=dfSlice$State[order(dfSlice$Crude.Rate,decreasing=TRUE)])

		ggplot(dfSlice,
			aes(State,Crude.Rate)) +
			geom_bar(stat="identity") +
			coord_flip() +
			ylab("Deaths per 100,000") +
			ggtitle(paste0(strwrap(input$cause,width=60),collapse="\n"))
	},height=700,width=525)
}

shinyApp(ui = ui, server = server)
