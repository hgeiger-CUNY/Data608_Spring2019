library(ggplot2)
library(dplyr)
library(shiny)

df <- read.csv("https://raw.githubusercontent.com/charleyferrari/CUNY_DATA_608/master/module3/data/cleaned-cdc-mortality-1999-2010-2.csv",
        header=TRUE,stringsAsFactors=FALSE)

df <- df[df$ICD.Chapter != "Codes for special purposes" & df$ICD.Chapter != "Diseases of the ear and mastoid process",] #Remove causes found in very few years/states.


ui <- fluidPage(
	headerPanel('Death rates over time in United States'),
	sidebarPanel(
		selectInput('cause','Cause of death',unique(df$ICD.Chapter),selected='Diseases of the circulatory system'),
		selectInput('state','State',unique(df$State),selected='TX')
	),
	mainPanel(
		plotOutput('plot1')
	)
)

server <- function(input, output) {
	output$plot1 <- renderPlot({
		state_of_interest <- df %>%
			filter(ICD.Chapter == input$cause,State == input$state)
		if(nrow(state_of_interest) == 0 | nrow(state_of_interest) == 1)
		{
			state_of_interest <- state_of_interest[,c("Year","Crude.Rate")]
			years_not_found <- setdiff(1999:2010,state_of_interest$Year)
			state_of_interest <- rbind(state_of_interest,data.frame(Year = years_not_found,
									Crude.Rate = rep(NA,times=length(years_not_found))))
			state_of_interest <- state_of_interest[order(state_of_interest$Year),]
		}
		other_states <- df %>%
			filter(ICD.Chapter == input$cause,State != input$state)
		other_states <- data.frame(Year = 1999:2010,Crude.Rate = aggregate(Deaths ~ Year,FUN=sum,data=other_states)$Deaths/(aggregate(Population ~ Year,FUN=sum,data=other_states)$Population / 100000))
		if(nrow(state_of_interest) >= 2)
		{
			to_plot <- data.frame(Year = c(state_of_interest$Year,other_states$Year),
				Crude.Rate = c(state_of_interest$Crude.Rate,other_states$Crude.Rate),
				State = rep(c(input$state,"All other states"),times=c(nrow(state_of_interest),12)))
			ggplot(to_plot,
				aes(Year,Crude.Rate)) +
				geom_line() +
				geom_point() +
				facet_wrap(~State,ncol=2,scales="free_y") +
				ggtitle(paste0(strwrap(input$cause,width=60),collapse="\n")) +
				ylab("Deaths per 100,000")
		}
	},width=600,height=600)
}

shinyApp(ui = ui, server = server)
