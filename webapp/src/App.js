import React, { Component } from 'react';
import logo from './logo.svg';
import './App.css';
import socketIOClient from 'socket.io-client'
import { Button , ButtonGroup, Alert, Input} from 'reactstrap';

class App extends Component {
    constructor(props){
        super(props);
        this.state = {
            runMode: 0,
            status: -1,
            serialData: 'Waiting on data...',
            endpoint: 'http://172.16.4.10/',
            response: '',
            cmdResponse: '',
            disableReset: false
        }
        const {endpoint} = this.state;
        this.socket = socketIOClient(endpoint);
        this.onModeSelectClick = this.onModeSelectClick.bind(this);
        this.onStepClick = this.onStepClick.bind(this);
    }

    onModeSelectClick(num) {
        this.setState({runMode: num});
    }

    onStepClick(){
        var self = this;
        self.setState({status: 1});
        if(self.state.status===-1){
            self.socket.emit('mode', self.state.runMode);
        }

        self.socket.emit('step', ()=>{
            console.log("step");
        });
    }

    onResetClick(){
        var self = this;
        self.setState({status: 1,
                        disableReset: true});

        self.socket.emit('reset', ()=>{
            console.log('Reset triggered!');
        });
    }

    getColor(){
        switch(this.state.status){
            case 0:
                return "success";

            case 1:
                return "warning";

            case 2:
                return "danger";

            default:
                return "secondary";
        }
    }

    getStatusText(){
        switch(this.state.status){
            case 0:
                return "Success!";

            case 1:
                return "Running...";

            case 2:
                return "ERROR!!!";

            default:
                return "Ready!";
        }
    }

    componentDidMount() {
        var self = this;
        // Got connection to server
        self.socket.on("connect", () => {
            console.log('Connected to server!');
        });

        // Got new log data
        self.socket.on('serialData', (data) => {
            self.setState({ response: data });
        });

        // Got new command data
        self.socket.on('cmdData', (data) => {
            self.setState({ cmdResponse: data });
        });

        self.socket.on('stepDone', (data)=>{
            console.log('Step complete');
            if(data === 1){
                self.setState({status: 0});
            } else if (data === -1){
                self.setState({status: 2});
            }
        });

        self.socket.on('resetDone', (data)=>{
            console.log('Reset complete!');
            if(data === 1){
                self.setState({status: -1,
                                response: '',
                                cmdResponse: '',
                                disableReset: false,});
            } else if (data === -1){
                self.setSetate({status: 2,
                                disableReset: true,});
            }
        });
    }

     render() {
         const { response } = this.state;
         const { cmdResponse } = this.state;
         return (
              <div className="App">
                <header className="App-header">
                <img src={logo} className="App-logo" alt="logo" />
                <h1 className="App-title">Automatic Vehicle Charger Controls</h1>
                </header>
                <div> </div>
                <div className="Container">
                <div className="ImgBox">
                    <img src="/video_feed" alt="Current detection feed"/>
                </div>
                <div className="Seperator">
                </div>
                <div className="ControlPane">
                <Alert color={this.getColor()}>
                    {this.getStatusText()}
                </Alert>

                <div>
                    Current Command:
                </div>

                <Input type="textarea" rows="1" value={cmdResponse} disabled>

                </Input>

                <div id="ModeSelect">
                    <div>
                    Mode Select:
                    </div>

                    <ButtonGroup>
                        <Button onClick={()=>this.onModeSelectClick(0)} active={this.state.runMode===0} disabled={!(this.state.status===-1) && !(this.state.runMode===0)}>
                            Auto
                        </Button>
                        <Button onClick={()=>this.onModeSelectClick(1)} active={this.state.runMode===1} disabled={!(this.state.status===-1) && !(this.state.runMode===1)}>
                            Step
                        </Button>
                    </ButtonGroup>
                </div>

                <div id="ButtonStart">
                    <Button onClick={() => this.onStepClick()} block disabled={this.state.status===1}>
                        {this.state.runMode===0 ? "Start" : "Step"}
                    </Button>
                </div>

                <div id="ButtonReset">
                    <Button onClick={() => this.onResetClick()} block disabled={this.state.disableReset}>
                        Reset
                    </Button>
                </div>

            </div>
        </div>

        <div className="footer">
            <p align="left">
                Live log:
            </p>
            <Input type="textarea" rows="4" value={response} disabled>
            </Input>
        </div>
    </div>
    );
    }
}



export default App;
